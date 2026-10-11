#!/usr/bin/env python3
"""阶段 B（dev151）结果分析：分类指标 + 配对比较 + 事前判据核验。

**只做统计与核验，不改动任何预测**。判据在 `docs/V2_STAGEB_FULL_PLAN.md` §6 事前写死。

用法：
    python scripts/v2_stageb_dev_analysis.py \
        --v1-root C:/1_yanjiusheng/BioEvidence/BioEvidence-v1 \
        --run-dir runs/P1-v2-stageB-order-20260924
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CONDS = ("B0_original", "B1_result_first", "B2_reversed", "B3_shuffled")
LABELS = ("yes", "no", "maybe")


def load_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def metrics(items: list[tuple[str, str, str]]) -> dict:
    """items = [(gold, pred_or_None, status)]；分母 = 全部条数，invalid 计错。"""
    n = len(items)
    n_ok = sum(1 for _g, _p, s in items if s == "ok")
    n_inv = sum(1 for _g, _p, s in items if s != "ok")
    correct = sum(1 for g, p, s in items if s == "ok" and p == g)
    per = {}
    for lab in LABELS:
        support = sum(1 for g, _p, _s in items if g == lab)
        tp = sum(1 for g, p, s in items if g == lab and s == "ok" and p == lab)
        fp = sum(1 for g, p, s in items if g != lab and s == "ok" and p == lab)
        fn = sum(1 for g, p, s in items if g == lab and not (s == "ok" and p == lab))
        prec = round(tp / (tp + fp), 4) if (tp + fp) else None
        rec = round(tp / (tp + fn), 4) if (tp + fn) else None
        if support == 0:
            f1 = None
        elif tp == 0:
            f1 = 0.0
        elif prec is None or (prec + rec) == 0:
            f1 = 0.0
        else:
            f1 = round(2 * prec * rec / (prec + rec), 4)
        per[lab] = {"support": support, "tp": tp, "fp": fp, "fn": fn,
                    "precision": prec, "recall": rec, "f1": f1}
    f1s = [v["f1"] for v in per.values() if v["f1"] is not None]
    return {"n": n, "n_ok": n_ok, "n_invalid": n_inv,
            "accuracy": round(correct / n, 4), "n_correct": correct,
            "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else None,
            "per_class": per}


def mcnemar_exact(b: int, c: int) -> dict:
    """精确 McNemar（二项检验，p=0.5）。"""
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "n_discordant": 0, "p_exact": 1.0}
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return {"b": b, "c": c, "n_discordant": n, "p_exact": round(min(1.0, 2 * tail), 5)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1-root", required=True)
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    root, run_dir = Path(args.v1_root), Path(args.run_dir)

    rows = load_jsonl(run_dir / "predictions_order_dev.jsonl")
    plan = json.loads((run_dir / "order_plan_all_samples.json").read_text(encoding="utf-8"))
    changed_input = {p["question_id"]: p["effective_intervention_conditions"]
                     for p in plan["plans"]}

    proc = root / "data/processed/pubmedqa"
    gold = {g["question_id"]: g["gold_label"] for g in load_jsonl(proc / "gold_labels.jsonl")}
    manifest = load_jsonl(root / "data/manifests/split_pubmedqa_qal_v1.jsonl") \
        if (root / "data/manifests/split_pubmedqa_qal_v1.jsonl").exists() else \
        load_jsonl(root / "data/manifests/split_pubmedqa_pqal_v1.jsonl")
    dev_ids = sorted(m["question_id"] for m in manifest
                     if m["scheme"] == "internal_70_30" and m["split"] == "dev")

    by_cond = {c: {r["question_id"]: r for r in rows if r["condition"] == c} for c in CONDS}

    # ---------- 主口径（151 条，invalid 计错） ----------
    main_m = {}
    for c in CONDS:
        items = []
        for q in dev_ids:
            r = by_cond[c].get(q)
            if r is None:
                items.append((gold[q], None, "invalid"))
            else:
                items.append((gold[q], r.get("label"), r.get("status")))
        # status ok 才给 pred；dataset 里 status 为 ok / invalid / invalid_citation
        items = [(g, (p if s == "ok" else None), s) for g, p, s in items]
        main_m[c] = metrics(items)

    # 平凡基线：恒答 yes
    trivial = metrics([(gold[q], "yes", "ok") for q in dev_ids])

    # ---------- 诊断指标 ----------
    def cited_any_result(r: dict) -> bool:
        rp = set(r.get("result_positions") or [])
        return any(c in rp for c in (r.get("citations") or []))

    diag = {}
    for c in CONDS:
        sub = [by_cond[c][q] for q in dev_ids if q in by_cond[c]]
        with_cit = [r for r in sub if r.get("citations")]
        diag[c] = {
            "n_with_citation": len(with_cit),
            "citation_result_family_rate": round(
                sum(1 for r in with_cit if cited_any_result(r)) / max(len(with_cit), 1), 4),
            "cited_E1_rate": round(
                sum(1 for r in with_cit if 1 in (r.get("citations") or []))
                / max(len(with_cit), 1), 4),
            "mean_output_chars": round(
                sum(len(r.get("raw_output") or "") for r in sub) / max(len(sub), 1), 1),
            "mean_item_seconds": round(
                sum(r.get("item_seconds", 0) for r in sub) / max(len(sub), 1), 3),
        }

    # ---------- 配对比较 ----------
    paired = {}
    for c in CONDS[1:]:
        pairs = []
        for q in dev_ids:
            b0, cx = by_cond["B0_original"].get(q), by_cond[c].get(q)
            if not b0 or not cx:
                continue
            same_input = cx.get("identical_to_baseline", False)
            ok = (b0.get("status") == "ok" and cx.get("status") == "ok")
            pairs.append(dict(q=q, same_input=same_input,
                              lbl_ch=b0.get("label") != cx.get("label"),
                              ans_ch=b0.get("answerable") != cx.get("answerable"),
                              disp_ch=sorted(b0.get("citations") or []) != sorted(cx.get("citations") or []),
                              b0_ok=ok and b0.get("label") == gold[q],
                              cx_ok=ok and cx.get("label") == gold[q]))
        eff = [p for p in pairs if not p["same_input"]]
        b = sum(1 for p in eff if p["b0_ok"] and not p["cx_ok"])
        cc_ = sum(1 for p in eff if not p["b0_ok"] and p["cx_ok"])
        paired[c] = {
            "n_pairs": len(pairs), "n_effective": len(eff),
            "n_same_input": len(pairs) - len(eff),
            "label_changed": sum(1 for p in eff if p["lbl_ch"]),
            "label_changed_rate": round(sum(1 for p in eff if p["lbl_ch"]) / max(len(eff), 1), 4),
            "abstain_changed": sum(1 for p in eff if p["ans_ch"]),
            "display_index_changed": sum(1 for p in eff if p["disp_ch"]),
            "mcnemar_vs_B0": mcnemar_exact(b, cc_),
            "accuracy_delta": round(main_m[c]["accuracy"] - main_m["B0_original"]["accuracy"], 4),
            "macro_f1_delta": round(main_m[c]["macro_f1"] - main_m["B0_original"]["macro_f1"], 4),
        }

    # cited-chunk 变化（需要 display_to_chunk 映射）
    cited_chunk = {}
    for c in CONDS[1:]:
        n_ch = 0
        n_eff = 0
        for q in dev_ids:
            b0, cx = by_cond["B0_original"].get(q), by_cond[c].get(q)
            if not b0 or not cx or cx.get("identical_to_baseline"):
                continue
            n_eff += 1
            f = lambda r: {r["display_to_chunk"].get(f"E{x}") for x in (r.get("citations") or [])}
            if f(b0) != f(cx):
                n_ch += 1
        cited_chunk[c] = {"n_effective": n_eff, "cited_chunk_set_changed": n_ch,
                          "rate": round(n_ch / max(n_eff, 1), 4)}

    # ---------- 事前判据核验 ----------
    b0r = diag["B0_original"]["citation_result_family_rate"]
    b1r = diag["B1_result_first"]["citation_result_family_rate"]
    delta_pp = round((b1r - b0r) * 100, 2)
    f1_drop_pp = round((main_m["B0_original"]["macro_f1"] - main_m["B1_result_first"]["macro_f1"]) * 100, 2)
    # 事前判据的**每一档都只定义下一步动作**，不构成机制结论。
    # （2026-09-24 更正 ERR-B1：原写法把「<5pp 档」读成「位置不是主因」，属解释越界。）
    if delta_pp >= 15 and f1_drop_pp <= 2:
        verdict = "命中 ≥15pp 且 F1 降 ≤2pp 档 → 行动：先做零训练的顺序策略修复"
    elif delta_pp < 5:
        verdict = "命中 <5pp 档 → 行动：不采纳该排序方案（结果族优先），阶段 C 转做目标重构（C-1/C-2）"
    else:
        verdict = "介于两档之间 → 行动：T 与 P 分别实验，一次只改一个因素"
    verdict_scope_note = (
        "**该档位只定义下一步动作，不构成机制结论。** 事前判据的三档是为决定「接下来做什么」，"
        "不是为回答「为什么」。因此本结果**不推出**「位置不是主因」，也**未排除**位置因素；"
        "训练目标偏置的因果作用**未被独立验证**。见 STAGEB_DEV_RESULTS.md §0 与 §6。")

    all_label_deltas = [abs(paired[c]["label_changed_rate"]) for c in CONDS[1:]]
    notes = {
        "invalid_or_invalid_citation_rate": round(
            sum(main_m[c]["n_invalid"] for c in CONDS) / (151 * 4), 4),
        "if_invalid_rate_gt_5pct": "需先查装配",
        "all_three_label_change_lt_5pct": all(x < 0.05 for x in all_label_deltas),
    }

    out = {
        "meta": {
            "task": "v2 阶段 B：dev151 顺序对照结果分析",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(run_dir),
            "n_dev": len(dev_ids),
            "criteria_source": "docs/V2_STAGEB_FULL_PLAN.md §6（事前写死）",
            "CAVEAT": ("『结果族引用率』与『E1 引用率』是**机制诊断指标**，不是正确性指标。"
                       "人工标注尚未用于本分析。"),
        },
        "main_denominator_151": main_m,
        "trivial_all_yes_baseline": trivial,
        "diagnostic_only": diag,
        "paired_effective_only": paired,
        "cited_chunk_change": cited_chunk,
        "pre_registered_verdict": {
            "B0_result_family_rate": b0r,
            "B1_result_family_rate": b1r,
            "B1_minus_B0_pp": delta_pp,
            "B1_macro_f1_drop_pp": f1_drop_pp,
            "verdict": verdict,
            "verdict_scope_note": verdict_scope_note,
            "secondary_checks": notes,
        },
    }
    (run_dir / "stageb_dev_analysis.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== 主口径（151 条，invalid 计错） ===")
    for c in CONDS:
        m = main_m[c]
        print(f"  {c:16} acc={m['accuracy']:.4f} macroF1={m['macro_f1']} "
              f"ok={m['n_ok']} inv={m['n_invalid']}")
    print(f"  {'(恒答 yes 基线)':16} acc={trivial['accuracy']:.4f} macroF1={trivial['macro_f1']}")
    print()
    print("=== 诊断指标（非正确性） ===")
    for c in CONDS:
        d = diag[c]
        print(f"  {c:16} 结果族引用率={d['citation_result_family_rate']:.4f} "
              f"E1引用率={d['cited_E1_rate']:.4f} 输出字符={d['mean_output_chars']} "
              f"t={d['mean_item_seconds']}s")
    print()
    print("=== 配对（仅输入真正变化者） ===")
    for c in CONDS[1:]:
        p = paired[c]
        print(f"  {c:16} n_eff={p['n_effective']} 标签变化={p['label_changed']} "
              f"({p['label_changed_rate']:.1%}) 弃答变化={p['abstain_changed']} "
              f"编号变化={p['display_index_changed']} | "
              f"accΔ={p['accuracy_delta']:+.4f} F1Δ={p['macro_f1_delta']:+.4f} "
              f"McNemar p={p['mcnemar_vs_B0']['p_exact']}")
    print()
    print("=== 实际引用片段变化（映射回 chunk） ===")
    for c in CONDS[1:]:
        x = cited_chunk[c]
        print(f"  {c:16} {x['cited_chunk_set_changed']}/{x['n_effective']} = {x['rate']:.1%}")
    print()
    print("=== 事前判据 ===")
    print(f"  B0 结果族引用率 = {b0r:.4f} → B1 = {b1r:.4f}，Δ = {delta_pp:+.2f} 个百分点")
    print(f"  macro-F1 降幅 = {f1_drop_pp:+.2f} 个百分点")
    print(f"  → 判定：{verdict}")
    print(f"  次级检查 = {json.dumps(notes, ensure_ascii=False)}")
    print(f"[written] {run_dir/'stageb_dev_analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
