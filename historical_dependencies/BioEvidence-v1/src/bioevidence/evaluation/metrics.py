#!/usr/bin/env python3
"""分类指标与逐条预测的评分器。

设计纪律（手册第 10 节）：
  * **无效输出按错误计**，不得从分母里静默删除。
  * **系统失败单列**，并且不能被藏起来——本模块同时报出「含系统失败」与「不含系统失败」两套口径。
  * 每个分数都必须能从逐条预测重新算出来，因此评分只依赖 (gold, pred, status) 三元组。
  * 小样本不用多位小数制造精确感：所有比率都附分子/分母。

状态取值（三选一，互斥）：
  ok        —— 成功生成且解析出合法标签
  invalid   —— 生成成功但输出无法解析出合法标签（算错）
  failure   —— 系统失败：超时、OOM、加载失败等（单列，不算错也不算对）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

LABELS: tuple[str, ...] = ("yes", "no", "maybe")

STATUS_OK = "ok"
STATUS_INVALID = "invalid"
STATUS_FAILURE = "failure"


@dataclass
class ItemResult:
    """一条预测的评分输入。只有这三个字段参与统计，保证结果可重算。"""

    question_id: str
    gold: str
    status: str
    pred: str | None = None          # status != ok 时必须为 None

    def __post_init__(self) -> None:
        if self.status not in (STATUS_OK, STATUS_INVALID, STATUS_FAILURE):
            raise ValueError(f"未知 status: {self.status}")
        if self.status == STATUS_OK and self.pred not in LABELS:
            raise ValueError(f"status=ok 但 pred 非法: {self.pred!r}")
        if self.status != STATUS_OK and self.pred is not None:
            raise ValueError(f"status={self.status} 时 pred 必须为 None，实际 {self.pred!r}")


@dataclass
class MetricBundle:
    """一组指标。所有比率都带分子分母。"""

    n_total: int = 0
    n_applicable: int = 0            # = n_total - n_failure
    n_failure: int = 0
    n_invalid: int = 0
    n_correct: int = 0

    accuracy: float | None = None            # 主口径：invalid 计错，分母 = n_applicable
    accuracy_including_failures: float | None = None   # 备查口径：分母 = n_total，failure 计错
    macro_f1: float | None = None
    per_class: dict = field(default_factory=dict)
    confusion: dict = field(default_factory=dict)
    parse_ok_rate: float | None = None       # n_ok / n_applicable
    invalid_rate: float | None = None        # n_invalid / n_applicable
    failure_rate: float | None = None        # n_failure / n_total
    counts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "n_total": self.n_total,
            "n_applicable": self.n_applicable,
            "n_failure": self.n_failure,
            "n_invalid": self.n_invalid,
            "n_correct": self.n_correct,
            "accuracy": self.accuracy,
            "accuracy_including_failures": self.accuracy_including_failures,
            "macro_f1": self.macro_f1,
            "per_class": self.per_class,
            "confusion": self.confusion,
            "parse_ok_rate": self.parse_ok_rate,
            "invalid_rate": self.invalid_rate,
            "failure_rate": self.failure_rate,
            "counts": self.counts,
            "denominator_policy": (
                "accuracy 的分母是 n_applicable（= n_total - n_failure），invalid 输出计为错误；"
                "n_failure 单列，不进入 accuracy 分母，但通过 accuracy_including_failures 一并报出。"
            ),
        }


def _safe_ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def compute_metrics(items: Sequence[ItemResult], labels: Iterable[str] = LABELS) -> MetricBundle:
    """从逐条结果计算指标。不依赖任何外部状态，可被反复重算。"""
    labels = tuple(labels)
    bundle = MetricBundle()
    bundle.n_total = len(items)
    if not items:
        return bundle

    bundle.n_failure = sum(1 for it in items if it.status == STATUS_FAILURE)
    bundle.n_invalid = sum(1 for it in items if it.status == STATUS_INVALID)
    bundle.n_applicable = bundle.n_total - bundle.n_failure
    bundle.n_correct = sum(
        1 for it in items if it.status == STATUS_OK and it.pred == it.gold
    )
    n_parse_ok = sum(1 for it in items if it.status == STATUS_OK)

    bundle.accuracy = _safe_ratio(bundle.n_correct, bundle.n_applicable)
    bundle.accuracy_including_failures = _safe_ratio(bundle.n_correct, bundle.n_total)
    bundle.parse_ok_rate = _safe_ratio(n_parse_ok, bundle.n_applicable)
    bundle.invalid_rate = _safe_ratio(bundle.n_invalid, bundle.n_applicable)
    bundle.failure_rate = _safe_ratio(bundle.n_failure, bundle.n_total)

    # 混淆矩阵：gold -> pred（只统计 status=ok；invalid/failure 单独计，不塞进任何格子）
    confusion = {g: {p: 0 for p in labels} for g in labels}
    confusion["__invalid__"] = {p: 0 for p in labels}
    confusion["__failure__"] = {p: 0 for p in labels}
    for it in items:
        if it.status == STATUS_OK:
            confusion[it.gold][it.pred] += 1
        elif it.status == STATUS_INVALID:
            confusion["__invalid__"][it.gold] += 1
        else:
            confusion["__failure__"][it.gold] += 1
    bundle.confusion = confusion

    # 逐类 P / R / F1
    #
    # 关键定义（手册第 10 节：macro-F1「固定标签集合，不能忽略稀有类别」）：
    #   只要某个类在本划分里有样本（support > 0），它就**必须**进入 macro 平均。
    #   如果模型从未预测该类，那么 tp = 0 → recall = 0 → F1 = 0（而不是「无值被跳过」）。
    #   只有 support == 0 的类才真正不参与平均。
    #   验证：全预测 yes 时，yes 的 F1 ≈ 0.711、no/maybe 的 F1 = 0，
    #   macro-F1 ≈ 0.237 —— 与理论上限一致，说明这个定义是对的。
    per_class: dict = {}
    for lab in labels:
        tp = sum(1 for it in items if it.status == STATUS_OK and it.gold == lab and it.pred == lab)
        fp = sum(1 for it in items if it.status == STATUS_OK and it.gold != lab and it.pred == lab)
        fn = sum(
            1 for it in items
            if it.gold == lab and not (it.status == STATUS_OK and it.pred == lab)
        )
        support = sum(1 for it in items if it.gold == lab)
        precision = _safe_ratio(tp, tp + fp)     # tp+fp=0 时为 None（未预测过该类）
        recall = _safe_ratio(tp, tp + fn)        # fn 含 invalid/failure，所以 invalid 会拉低 recall

        if support == 0:
            f1 = None
        elif tp == 0:
            f1 = 0.0
        elif precision is None or (precision + recall) == 0:
            f1 = 0.0
        else:
            f1 = round(2 * precision * recall / (precision + recall), 4)

        per_class[lab] = {
            "tp": tp, "fp": fp, "fn": fn, "support": support,
            "precision": precision, "recall": recall, "f1": f1,
            "excluded_from_macro": support == 0,
            "note": (
                "support>0 但 tp=0 时 f1 记为 0（该类必须参与 macro 平均，不得被跳过）；"
                "recall 的 fn 包含 invalid/failure 输出，因此 recall 会低于只看 ok 的口径。"
            ),
        }
    bundle.per_class = per_class

    f1_values = [v["f1"] for v in per_class.values() if v["f1"] is not None]
    bundle.macro_f1 = round(sum(f1_values) / len(f1_values), 4) if f1_values else None

    bundle.counts = {
        "n_ok": n_parse_ok,
        "gold_distribution": {lab: sum(1 for it in items if it.gold == lab) for lab in labels},
        "pred_distribution": {
            lab: sum(1 for it in items if it.status == STATUS_OK and it.pred == lab)
            for lab in labels
        },
    }
    return bundle


def majority_class_baseline(items: Sequence[ItemResult], label: str = "yes") -> MetricBundle:
    """E0：全预测同一标签。不接受手工给的指标，必须走与模型相同的评分路径。"""
    forced = [
        ItemResult(question_id=it.question_id, gold=it.gold, status=STATUS_OK, pred=label)
        for it in items
    ]
    return compute_metrics(forced)


def error_breakdown(items: Sequence[ItemResult]) -> dict:
    """错误分层：把错误按类型与标签拆开，便于后续归因。"""
    wrong = [it for it in items if not (it.status == STATUS_OK and it.pred == it.gold)]
    by_status: dict[str, int] = {}
    for it in wrong:
        by_status[it.status] = by_status.get(it.status, 0) + 1
    by_pair: dict[str, int] = {}
    for it in wrong:
        key = f"{it.gold}->{it.pred if it.pred else it.status}"
        by_pair[key] = by_pair.get(key, 0) + 1
    return {
        "n_wrong": len(wrong),
        "by_status": by_status,
        "by_gold_to_pred": dict(sorted(by_pair.items(), key=lambda kv: -kv[1])),
        "wrong_question_ids": [it.question_id for it in wrong],
    }
