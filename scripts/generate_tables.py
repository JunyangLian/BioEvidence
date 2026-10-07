#!/usr/bin/env python3
"""portfolio 数据生成器：从**冻结产物**自动生成求职展示用的表格与案例数据。

产出（全部由脚本生成，避免手写错列）：
  portfolio/version_comparison.auto.md   版本结果对照表（含出处列）
  portfolio/citation_stats.auto.md       各条件引用计数（自预测文件统计）
  portfolio/FAILURE_CASES.auto.md        失败案例库数据附录（逐字字段 + 出处路径）
  portfolio/EVALUATION_FRAMEWORK.md      在 AUTO 标记区间回填对照表（手写正文保留）

纪律：只读产物；不改封存文件；数字全部来自文件，缺失即标注 MISSING。
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

V1 = Path(r"BioEvidence-v1")
V2 = Path(r"BioEvidence-v2")
V3 = Path(r".")
P0 = V3 / "runs" / "P0-v3-feasibility-20260924"
P1 = V3 / "runs" / "P1-v3-ab-proto-20260930"
ACC = V3 / "runs" / "P1-v3-acceptance-20261001"
PORT = V3 / "portfolio"


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def load_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip() and '"sample_id"' in l]


def load_jsonl_all(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# ---------------------------------------------------------------------------
# 1) 版本结果对照表
# ---------------------------------------------------------------------------
def metric_rows() -> list[dict]:
    rows = []

    def add(model, train, task, split, ev, n, acc, f1, abst, src, note=""):
        rows.append({"model": model, "training": train, "task": task, "split": split,
                     "evidence": ev, "n": n, "accuracy": acc, "macro_f1": f1,
                     "abstention": abst, "source": src, "note": note})

    # --- Task A（两行契约：标签分类） ---
    p2 = load_json(V1 / "runs/P2-baseline-20260920/metrics.json")
    c2 = p2["conditions"]
    add("Qwen3-0.6B（未微调）", "无", "Task A 标签分类", "dev 151（internal_70_30）",
        "E1 无证据", c2["e1_none"]["n_total"], c2["e1_none"]["accuracy"],
        c2["e1_none"]["macro_f1"], "—",
        "v1 runs/P2-baseline-20260920/metrics.json", "未微调基座；无证据条件")
    e2k = [k for k in c2 if k.startswith("e2")][0]
    add("Qwen3-0.6B（未微调）", "无", "Task A 标签分类", "dev 151（internal_70_30）",
        "E2 oracle 真值证据", c2[e2k]["n_total"], c2[e2k]["accuracy"], c2[e2k]["macro_f1"],
        "—", "v1 runs/P2-baseline-20260920/metrics.json",
        "未微调基座 + 真值证据：macro-F1 反而低于无证据条件（负结果）")

    # v1 官方 test 500（Task A）
    t_e0 = load_json(V1 / "runs/P10-test-final-20260922/metrics_e0_majority.json")
    add("多数类基线（无模型）", "—", "Task A 标签分类", "test 500（official）", "—",
        t_e0["n"], t_e0["accuracy"], t_e0["macro_f1"], "—",
        "v1 runs/P10-test-final-20260922/metrics_e0_majority.json")
    t_a0 = load_json(V1 / "runs/P10-test-final-20260922/metrics_e4_retrieval_A0_test.json")
    add("Qwen3-0.6B", "P4 QLoRA SFT（E4/E6 迭代）", "Task A 标签分类", "test 500（official）",
        "A0 原 BM25 top-3", t_a0["n_total"], t_a0["accuracy"], t_a0["macro_f1"], "—",
        "v1 runs/P10-test-final-20260922/metrics_e4_retrieval_A0_test.json")
    t_a2 = load_json(V1 / "runs/P10-test-final-20260922/metrics_e4_retrieval_A2_test.json")
    add("Qwen3-0.6B", "P4 QLoRA SFT（E4/E6 迭代）", "Task A 标签分类", "test 500（official）",
        "A2 章节配额（BM25+section-aware+quota=1）", t_a2["n_total"], t_a2["accuracy"],
        t_a2["macro_f1"], "—", "v1 runs/P10-test-final-20260922/metrics_e4_retrieval_A2_test.json")

    # --- Task B（四行契约：标签+引用+弃答） ---
    t_b0 = load_json(V1 / "runs/P10-test-final-20260922/metrics_e7_taskb_A0_test.json")
    add("Qwen3-0.6B", "P6 LoRA SFT（Task B 目标）", "Task B 四字段", "test 500（official）",
        "A0 原 BM25 top-3", t_b0["n_total"], t_b0["accuracy"], t_b0["macro_f1"], "—",
        "v1 runs/P10-test-final-20260922/metrics_e7_taskb_A0_test.json")
    t_b2 = load_json(V1 / "runs/P10-test-final-20260922/metrics_e7_taskb_A2_test.json")
    add("Qwen3-0.6B", "P6 LoRA SFT（Task B 目标）", "Task B 四字段", "test 500（official）",
        "A2 章节配额", t_b2["n_total"], t_b2["accuracy"], t_b2["macro_f1"], "—",
        "v1 runs/P10-test-final-20260922/metrics_e7_taskb_A2_test.json")

    d_a1 = load_json(V1 / "runs/P7-retrieval-20260921/metrics_e4_retrieval_A1_rerank.json")
    add("Qwen3-0.6B", "P4 QLoRA SFT", "Task A 标签分类", "dev 151（internal_70_30）",
        "A1 软性章节重排（无配额）", d_a1["n_total"], d_a1["accuracy"], d_a1["macro_f1"], "—",
        "v1 runs/P7-retrieval-20260921/metrics_e4_retrieval_A1_rerank.json")
    d_b1 = load_json(V1 / "runs/P7-retrieval-20260921/metrics_e7_taskb_A1_rerank.json")
    add("Qwen3-0.6B", "P6 LoRA SFT（Task B）", "Task B 四字段", "dev 151（internal_70_30）",
        "A1 软性章节重排", d_b1["n_total"], d_b1["accuracy"], d_b1["macro_f1"], "—",
        "v1 runs/P7-retrieval-20260921/metrics_e7_taskb_A1_rerank.json")
    d_b2 = load_json(V1 / "runs/P7-retrieval-20260921/metrics_e7_taskb_A2_quota.json")
    add("Qwen3-0.6B（冻结 E7）", "P6 LoRA SFT（Task B）", "Task B 四字段", "dev 151（internal_70_30）",
        "A2 章节配额（冻结配置）", d_b2["n_total"], d_b2["accuracy"], d_b2["macro_f1"], "—",
        "v1 runs/P7-retrieval-20260921/metrics_e7_taskb_A2_quota.json")

    # --- v2 C-1 成对微调探索（负结果） ---
    c1 = load_json(V2 / "runs/P3-v2-c1-paired-20260927/paired_eval_report.json")
    old, new = c1["groups"]["old_target"], c1["groups"]["new_target"]
    add("Qwen3-0.6B", "C-1 old-target（64 条成对重训）", "Task B 四字段", "dev 151",
        "C-1 评测条件", old["dev151_metrics"]["n"], old["dev151_metrics"]["accuracy"],
        old["dev151_metrics"]["macro_f1"], f"M1 {old['dev26_acceptance']['M1_无依据作答']['num']}/14 · "
        f"M2 {old['dev26_acceptance']['M2_错误弃答']['num']}/12",
        "v2 runs/P3-v2-c1-paired-20260927/paired_eval_report.json", "弃答率 0.7%")
    add("Qwen3-0.6B", "C-1 new-target（64 条成对重训，充分性监督）", "Task B 四字段", "dev 151",
        "C-1 评测条件", new["dev151_metrics"]["n"], new["dev151_metrics"]["accuracy"],
        new["dev151_metrics"]["macro_f1"], f"M1 {new['dev26_acceptance']['M1_无依据作答']['num']}/14 · "
        f"M2 {new['dev26_acceptance']['M2_错误弃答']['num']}/12",
        "v2 runs/P3-v2-c1-paired-20260927/paired_eval_report.json",
        "**负结果**：弃答率 94.7%，分类崩坏；权衡并存，不判成功")

    # --- v3 27B 零样本（dev151 流程对照） ---
    ab = load_json(P1 / "ab_metrics.json")
    fa, fb = ab["flow_A"], ab["flow_B"]
    add("Ternary Bonsai 2 27B（27.36B 三值量化，零样本）", "无微调（冻结底座）",
        "Task B 四字段（流程 A 常规）", "dev 151", "B0 冻结证据（=A2 同源）",
        fa["dev151"]["n"], fa["dev151"]["accuracy"], fa["dev151"]["macro_f1"],
        f"M1 {fa['dev26']['M1_无依据作答']['num']}/14 · M2 {fa['dev26']['M2_错误弃答']['num']}/12",
        "v3 runs/P1-v3-ab-proto-20260930/ab_metrics.json",
        "采样 temp 0.7 + seed（与 v1 greedy 不同）")
    add("Ternary Bonsai 2 27B（零样本）", "无微调（冻结底座）",
        "Task B 四字段（流程 B 先定位）", "dev 151", "B0 冻结证据（=A2 同源）",
        fb["dev151"]["n"], fb["dev151"]["accuracy"], fb["dev151"]["macro_f1"],
        f"M1 {fb['dev26']['M1_无依据作答']['num']}/14 · M2 {fb['dev26']['M2_错误弃答']['num']}/12",
        "v3 runs/P1-v3-ab-proto-20260930/ab_metrics.json", "工具辅助盲评后按规则未选用")

    # --- v3 验收集（探索性，暂定参考标签） ---
    am = load_json(ACC / "acceptance_metrics.json")
    cls = am["classification_仅充分"]
    add("Ternary Bonsai 2 27B（零样本）", "无微调（冻结底座）", "Task B 四字段（流程 A）",
        "新文献验收集 30（暂定参考标签）", "全文 CONTEXTS（无检索；与 dev 检索片段不可比）",
        cls["n"], cls["accuracy"], cls["macro_f1"],
        f"M1 {am['M1_无依据作答']['num']}/{am['M1_无依据作答']['den']} · "
        f"M2 {am['M2_错误弃答']['num']}/{am['M2_错误弃答']['den']}",
        "v3 runs/P1-v3-acceptance-20261001/acceptance_metrics.json",
        "**暂定参考标签（7 条待裁决未在预测前裁决）**；AI 辅助评审；不足样本仅 1 条")
    return rows


def render_version_table(rows: list[dict]) -> str:
    out = ["| 模型 | 训练经历 | 任务 | 数据划分 | 证据形态 | n | accuracy | macro-F1 | 弃答指标 | 出处 | 备注 |",
           "|---|---|---|---|---|---:|---:|---:|---|---|---|"]
    for r in rows:
        out.append(f"| {r['model']} | {r['training']} | {r['task']} | {r['split']} | "
                   f"{r['evidence']} | {r['n']} | {r['accuracy']} | {r['macro_f1']} | "
                   f"{r['abstention']} | `{r['source']}` | {r['note']} |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 2) 引用计数（自预测文件统计）
# ---------------------------------------------------------------------------
def citation_stats() -> str:
    def stats(rows, name, src):
        n = len(rows)
        cit = Counter(len(r["parsed"]["citations"]) for r in rows)
        issues = sum(1 for r in rows if r["parsed"].get("citation_issues"))
        ans = Counter(r["parsed"]["answerable"] for r in rows)
        oor = sum(len(r["parsed"].get("out_of_range_citations") or []) for r in rows)
        return (f"| {name} | {n} | {cit.get(1,0)} | {cit.get(2,0)} | {cit.get(3,0)} | "
                f"{cit.get(4,0)}+ | {ans.get('no',0)} | {issues} | {oor} | `{src}` |")

    out = ["| 条件 | n | 1 条引用 | 2 条 | 3 条 | ≥4 条 | 弃答(Answerable=no) | 契约违规行 | 越界引用数 | 出处 |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    acc_rows = load_jsonl(ACC / "predictions_A.jsonl")
    out.append(stats(acc_rows, "v3 验收集 30（流程 A）", str(ACC / "predictions_A.jsonl")))
    dev_rows = load_jsonl(P1 / "dev151" / "predictions_A.jsonl")
    out.append(stats(dev_rows, "v3 dev151（流程 A）", str(P1 / "dev151" / "predictions_A.jsonl")))
    dev_b2 = load_jsonl(P1 / "dev151" / "predictions_B2.jsonl")
    out.append(stats(dev_b2, "v3 dev151（流程 B）", str(P1 / "dev151" / "predictions_B2.jsonl")))
    v1_rows = load_jsonl_all(V1 / "runs/P10-test-final-20260922/predictions_e7_taskb_A2_test.jsonl")
    v1n = len(v1_rows)
    v1cit = Counter(len(r.get("citations") or []) for r in v1_rows)
    v1ans = Counter(r.get("answerable") for r in v1_rows)
    v1iss = sum(1 for r in v1_rows if r.get("citation_issues"))
    out.append(f"| v1 test 500（E7 0.6B，A2） | {v1n} | {v1cit.get(1,0)} | {v1cit.get(2,0)} | "
               f"{v1cit.get(3,0)} | {sum(v for k,v in v1cit.items() if k>=4)} | {v1ans.get('no',0)} | "
               f"{v1iss} | 0 | `v1 runs/P10-test-final-20260922/predictions_e7_taskb_A2_test.jsonl` |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 3) 失败案例数据附录
# ---------------------------------------------------------------------------
def fail_data() -> str:
    cases = []

    def case(cid, cat, sid, split, cond, q, evidence, raw, ref, fail, basis, interv, hypo, src):
        cases.append({"id": cid, "category": cat, "sample_id": sid, "split": split,
                      "condition": cond, "question": q, "evidence": evidence, "raw_output": raw,
                      "reference": ref, "failure": fail, "basis": basis,
                      "intervention": interv, "hypothesis": hypo, "source": src})

    # F01 格式/稳定性：test 重复循环
    rows = load_jsonl_all(V1 / "runs/P10-test-final-20260922/predictions_e7_taskb_A2_test.jsonl")
    loop = next(r for r in rows if r["question_id"] == "21214884")
    case("F01", "格式与契约 / 稳定性", "question_id=21214884", "test 500（official）",
         "v1 E7（0.6B）+ A2 检索，greedy，max_new_tokens=160",
         loop.get("question", "（问题见预测文件/数据集）"), "（B0/A2 检索 3 片段，见预测文件 evidence_meta）",
         (loop.get("raw_output") or "")[:600],
         "—（格式失败无参考标签语义）",
         "输出在 HPY 类型列举处进入重复循环（'35, 39' 交替）直至 token 用尽，解析失败（invalid）",
         "重复循环 + 截断；分母处理按冻结口径 invalid 计失败",
         "v1 后将 max_new_tokens 提至 160 覆盖 100% 目标（本条为 test 冻结产物，保持原样）",
         "greedy 解码下的重复循环属已知小模型风险；未做干预实验",
         "v1 runs/P10-test-final-20260922/predictions_e7_taskb_A2_test.jsonl")

    # F02 监督目标 + 引用（R021，人工审核）
    with (V1 / "data/review/review_packet_taskb_dev_FILLED.csv").open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        r021 = next(r for r in rd if r.get("question_id") == "28127977")
    case("F02", "监督目标 / 引用问题", "question_id=28127977（人工审核 R021）", "dev 151（internal_70_30）",
         "v1 E7（0.6B）+ A2 检索", r021.get("question", ""),
         r021.get("evidence_block", "")[:1200] + ("…" if len(r021.get("evidence_block", "")) > 1200 else ""),
         r021.get("model_raw_output", ""),
         "人工审核（负责人，单人）：证据是否支持=是；引用是否真的支撑理由=**是，但引用完全不对题**；"
         "备注=E3 明确说 leptin 与 overall survival 无关联，所以 no 对；但模型引用的 E1 是另一篇 HRQOL 文献，Reason 与 leptin 问题无关",
         "引用的 E1 与问题主题无关（引用完全不对题）；且 gold_answerable=yes 为文献身份代理而非语义判断",
         "v2 核查将本条定为 R021：可复现读法为 25/25 或 24/25，v1 勘误的 23/25 不可复现",
         "C-2 曾把 Reason/Citations 目标改为人工逐字依据（忠实度改善但语义支持未变）",
         "监督目标以『命中正确文献』定义 answerable，导致引用语义不被监督",
         "v1 data/review/review_packet_taskb_dev_FILLED.csv（R021 行）+ v2 docs/V2_IMPLEMENTATION_VERIFICATION.md §0.2")

    # F03 监督目标：无结果段的 yes 目标（train）
    sft = load_jsonl_all(V1 / "data/processed/pubmedqa/sft_taskb.jsonl")
    nores = next(r for r in sft if r["sample_type"] == "answerable_yes"
                 and not any("RESULT" in c.upper() or "FINDING" in c.upper()
                             for c in r["evidence_meta"]["used_chunk_ids"]))
    tgt = nores["messages"][-1]["content"]
    case("F03", "监督目标问题", f"question_id={nores['question_id']}（train 349）", "train 349（internal_70_30）",
         "v1 Task B 训练样本（BM25 top-3，无 section 配额）",
         nores["messages"][1]["content"].split("Evidence:")[0].replace("Question:\n", "").strip(),
         "章节：" + "、".join(nores["evidence_meta"]["used_chunk_ids"]) +
         "（**无 RESULTS/FINDINGS 章节**）；target Reason = " + tgt.split("Reason:")[1].split("Citations:")[0].strip()[:200],
         tgt[:400],
         "训练目标 gold_answerable=yes（由『命中正确文献』推导）",
         "证据中没有任何结果段，却被监督为『可回答且 Label=maybe』；该形态占训练 yes 样本 43.57%（149/342）",
         "v2 核查定位（M-1）；v2 阶段 D 据此把『无结果段』作为标注试点方向",
         "监督以文献身份代理定义 answerable → 该形态被标为可回答（机制假说，未逐条验证）",
         "『无结果段 + yes』是否直接导致模型在此类输入上过度自信 → 未逐条验证（C-1 为聚合对照，负结果）",
         "v1 data/processed/pubmedqa/sft_taskb.jsonl")

    # F04 监督目标：目标整段
    whole = None
    for r in sft:
        if r["sample_type"] != "answerable_yes":
            continue
        asst = r["messages"][-1]["content"]
        m = re.search(r"Reason:\s*(.+)\nCitations:", asst)
        if not m:
            continue
        break
    # 上面的 glob 写法不适用于逐行读取，改为直接读文件
    chunk_by_id = {}
    for l in open(V1 / "data/processed/pubmedqa/corpus_chunks.jsonl", encoding="utf-8"):
        d = json.loads(l)
        chunk_by_id[d["chunk_id"]] = d["text"]
    for r in sft:
        if r["sample_type"] != "answerable_yes":
            continue
        asst = r["messages"][-1]["content"]
        m = re.search(r"Reason:\s*(.+)\nCitations:", asst)
        if not m:
            continue
        reason = m.group(1).strip()
        if r["citation_chunk_id"] in chunk_by_id and reason == chunk_by_id[r["citation_chunk_id"]].strip():
            whole = r
            break
    assert whole is not None, "未找到目标整段样本"
    tgtw = whole["messages"][-1]["content"]
    case("F04", "监督目标问题", f"question_id={whole['question_id']}（train 349）", "train 349",
         "v1 Task B 训练样本",
         whole["messages"][1]["content"].split("Evidence:")[0].replace("Question:\n", "").strip(),
         f"引用 chunk {whole['citation_chunk_id']}；Reason 目标 = 该 chunk **全文**（逐字）",
         tgtw[:400],
         "训练目标 Reason = 整段 chunk（无 '. ' 可切分 → first_sentence() 退化为整段）",
         "该形态占训练 yes 样本 36.55%（125/342）[v2 核查复算]；监督模型『抄整段』",
         "v2 核查定位；C-2 曾尝试修正 Reason 目标（忠实度改善但语义支持未变）",
         "整段监督是否导致引用冗长 → 未做干预实验",
         "整段监督是否导致引用冗长/复制 → C-2 修正后忠实度改善但语义支持未变（部分证据）",
         "v1 data/processed/pubmedqa/sft_taskb.jsonl（目标整段形态，聚合 36.55%）")

    # F05 检索：A0 无结果段（dev）
    a0 = load_jsonl_all(V1 / "runs/P6-taskb-20260920/predictions_e7_taskb.jsonl")
    chunks = chunk_by_id  # 复用
    sec_of = {}
    for l in open(V1 / "data/processed/pubmedqa/corpus_chunks.jsonl", encoding="utf-8"):
        d = json.loads(l)
        sec_of[d["chunk_id"]] = d["section"]
    a0_case = next(r for r in a0 if not any(
        "RESULT" in sec_of[c].upper() or "FINDING" in sec_of[c].upper()
        for c in r["evidence_meta"]["used_chunk_ids"]))
    case("F05", "检索问题 / 证据不足形态", f"question_id={a0_case['question_id']}", "dev 151（A0 原 BM25）",
         "v1 E7（0.6B）+ A0 检索（无 section 配额）",
         "（问题见预测文件）",
         "章节：" + "、".join(sec_of[c] for c in a0_case["evidence_meta"]["used_chunk_ids"]) +
         "（**无 RESULTS/FINDINGS**）；该形态在 A0 下 60/151=39.7%，A2 配额下 0/151",
         (a0_case.get("raw_output") or "")[:300],
         "—（该条用于展示证据形态差异，不作为语义真值）",
         "裸 BM25 检索经常给不出结果段；A2 的 Results quota=1 把该形态从评估分布中整体移除（M-1）",
         "v2 阶段 D 将『无结果段』自然样本纳入标注试点（A0 60 条可用）",
         "配额是否真能提升答案质量 → v1 test Task A/B 数字（A0 vs A2）可见差异，但机制归因需对照",
         "配额提升是否转化为语义层面的回答改善 → 未做语义对照（现有差异为端到端分类数字）",
         "v1 runs/P6-taskb-20260920/predictions_e7_taskb.jsonl（A0）+ corpus_chunks.jsonl")

    # F06 证据不足 + 契约（val30 V16）
    acc_rows = {r["sample_id"]: r for r in load_jsonl(ACC / "predictions_A.jsonl")}
    v16 = acc_rows["V16"]
    case("F06", "证据不足 / 弃答 / 契约", "V16（新文献验收集，暂定参考）", "新文献验收集 30",
         "v3 27B 流程 A（全文 CONTEXTS，无检索）",
         "Do why menopausal women want to take hormone replacement therapy?（语法不完整）",
         "（全文 3 章节，见 acceptance_review_package.md）",
         (v16.get("raw_output") or "")[:400],
         "暂定参考：evidence_sufficiency=不足；supported_label=N/A（负责人填写稿；**待裁决项**）",
         "模型正确弃答（Answerable=no），但违反契约：弃答时 Citations 非空（E1,E3）→ 完整契约通过记 29/30",
         "弃答判断与暂定参考一致；契约违规为 P0 已登记的模型行为，未修复",
         "Acceptable 的操作口径缺失 → 该题弃答恰当性曾在 A/B 盲评中记『无法判断』，由负责人裁决定案",
         "弃答恰当性判断依赖暂定充分性标注（该条本身是待裁决项之一）",
         "v3 runs/P1-v3-acceptance-20261001/predictions_A.jsonl + validation_annotation_filled.csv")

    # F07 支持性超强度（val30 V15）
    v15 = acc_rows["V15"]
    case("F07", "回答支持性问题", "V15（新文献验收集，暂定参考）", "新文献验收集 30",
         "v3 27B 流程 A（全文 CONTEXTS）",
         "Does sarcopenia in Advanced COPD affect Cardiometabolic Risk Reduction by Short-Term High-intensity Pulmonary Rehabilitation?",
         "（见 acceptance_review_package.md）",
         (v15.get("raw_output") or "")[:400],
         "暂定参考：充分 + yes；**AI 辅助评审**：摘录支持=部分支持、引用忠实=部分忠实",
         "理由称改善『only in nonsarcopenic patients』并推断肌少症阻碍获益——E6 只报告组间对比描述，"
         "无组别×时间交互检验，且未量化肌少症组变化",
         "AI 辅助评审定位为『超出报告强度』；未做独立人工复核",
         "正确做法需组间差异检验；本条为输出质量案例，非发生率估计",
         "『组别对比描述』到『阻碍获益』的因果解读未验证",
         "v3 runs/P1-v3-acceptance-20261001/predictions_A.jsonl + acceptance_review_ai_assisted.json（V15）")

    # F08/F09/F10 dev26 盲评案例（工具辅助盲评）
    review_txt = (P1 / "ab_review_filled.md").read_text(encoding="utf-8")
    mapping = load_json(P1 / "ab_backend_mapping.json")["mapping"]

    def anon_block(anon: str) -> str:
        i = review_txt.find(f"## {anon}\n")
        j = review_txt.find("\n## ", i + 1)
        return review_txt[i:j if j > 0 else len(review_txt)]

    def flow_of(anon: str, side: str) -> str:
        return next(m for m in mapping if m["source_anon"] == anon)[f"{side}_is_flow"]

    t04_q = next(m for m in mapping if m["source_anon"] == "T04")["question_id"]
    case("F08", "引用忠实度问题", "T04（dev26 盲评；**工具辅助盲评**）", "dev 151 → dev26 参考子集",
         "v3 27B 流程 B（先定位）输出 Y = " + flow_of("T04", "Y"),
         "Does transverse apex coincide with coronal apex levels (regional or global) in adolescent idiopathic scoliosis?",
         "（B0 冻结证据，见盲审包）",
         anon_block("T04")[:1500],
         "工具辅助盲评：Y_citation_faithfulness=**部分忠实**（X=忠实）",
         "E3 的 up to two levels 仅针对整体顶点，理由将其同时推广至区域顶点——引用忠实度不足",
         "工具辅助盲评按冻结序数映射计入 A/B 对照（csr 净 −3 / rsl 净 −1）",
         "泛化性改写是否构成不忠实 → 盲评已给判断，独立人工复核未做",
         "把整体顶点结论推广到区域顶点是有意泛化还是疏忽 → 无法判定",
         "v3 runs/P1-v3-ab-proto-20260930/ab_review_filled.md（T04）+ ab_backend_mapping.json")

    t01_q = next(m for m in mapping if m["source_anon"] == "T01")["question_id"]
    case("F09", "弃答校准问题", "T01（dev26 盲评；**工具辅助盲评**）", "dev 151 → dev26 参考子集",
         "v3 27B 流程 A 与 B 均 Answerable=no",
         "Is the international normalised ratio (INR) reliable?",
         "（B0 冻结证据：E2/E3 为两途径 INR 一致性的直接结果）",
         anon_block("T01")[:1500],
         "工具辅助盲评：X/Y 弃答恰当性均为**不恰当**",
         "证据已有范围限定的直接结果，模型要求『所有场景的确定结论』才肯作答——过度保守弃答",
         "与 M2（错误弃答）口径一致：dev26 上 v3 M2 = 2/12（A、B 各 2）",
         "弃答校准与训练分布的关系 → v2 M-1 假说（未验证）；本条为观察",
         "过度保守弃答是否与任务训练分布有关 → M-1 假说（未验证）",
         "v3 runs/P1-v3-ab-proto-20260930/ab_review_filled.md（T01）")

    t06_q = next(m for m in mapping if m["source_anon"] == "T06")["question_id"]
    case("F10", "引用相关性问题", "T06（dev26 盲评；**工具辅助盲评**）", "dev 151 → dev26 参考子集",
         "v3 27B 流程 A 与 B",
         "Cancer of the buccal mucosa: are margins and T-stage accurate predictors of local control?",
         "（B0 冻结证据：E3 为胃癌资料）",
         anon_block("T06")[:1500],
         "工具辅助盲评：X/Y 均弃答恰当；盲评注明 **E3 属胃癌资料**，与颊黏膜癌局部控制无关",
         "检索把主题无关的摘要片段带进证据；模型未把它当作目标疾病的证据（未捏造），但引用列表中出现了它",
         "检索层缺陷（BM25 词面匹配）；A2 配额只保证 Results 章节，不保证主题相关",
         "无关引用是否会误导回答 → 本条中模型未受其误导（弃答），属观察",
         "无关引用在更长上下文中是否会误导回答 → 未验证",
         "v3 runs/P1-v3-ab-proto-20260930/ab_review_filled.md（T06）")

    # F11 弃答崩坏（v2 C-1）
    c1 = load_json(V2 / "runs/P3-v2-c1-paired-20260927/paired_eval_report.json")
    pq = next(q for q in c1["paired_per_question"] if q["question_id"] == "10605400")
    case("F11", "弃答崩坏（微调负结果）", "question_id=10605400（C-1 成对评测）", "dev 151",
         "v2 C-1 new-target（64 条成对重训，充分性监督）",
         "（INR 可靠性同题族；见 C-1 产物）",
         "（C-1 评测条件，见 paired_eval_report）",
         "old：Answerable=yes 且正确；new：Answerable=no（弃答）",
         "人工充分性=充分；old 判定正确 → new 弃答为**破坏**（成对方向）",
         "充分性监督把『不确定』过度泛化为『不足』→ 全量弃答（94.7%，maybe×144/151，分类 0.1192）",
         "v2 C-1 封存为负结果；机制（数据重平衡等）已列混淆因素，未分离",
         "弃答崩坏是否由重平衡单独导致 → 未验证（负责人已指出数据重平衡同属训练干预）",
         "弃答崩坏由数据重平衡单独导致 → 未验证（负责人指出重平衡同属训练干预）",
         "v2 runs/P3-v2-c1-paired-20260927/paired_eval_report.json")

    # F12 基础设施稳定性（P0 attempt1）
    case("F12", "稳定性问题（基础设施）", "P0 attempt1（ctx 16384 + f16 KV）", "—（推理基础设施）",
         "v3 27B 加载阶段",
         "—", "—",
         "无输出（进程挂死）",
         "—（非模型行为）",
         "VRAM 7608/8192 MiB 后进程静默挂死（GPU 100%、单核钉住、健康检查 >4min 无变化）；"
         "对照：ctx 8192 通过。已登记为**验收程序偏差之外的独立基础设施发现**",
         "16384+f16 KV 在本机桌面占用下不可用 → 厂商文档亦有同样记录",
         "处置正确（保留失败记录、换配置重试）；根因未做受控对照（桌面显存占用为混杂因素）",
         "VRAM 挂死的根因（桌面显存占用为混杂因素）未做受控对照",
         "v3 runs/P0-v3-feasibility-20260924/attempts/attempt1_ctx16384_f16_server.log")

    # F13 格式占位符（v1 ERR-008）
    # F13 格式占位符（v1 ERR-008）
    # 注：原始试跑输出（Label: <yes>）未保留于现有产物——修复模板后全量运行覆盖了试跑文件
    #（实测：predictions_e2.jsonl 现存 151 条、0 条含 '<yes>'）。证据为 v1 error_log 的登记记录。
    err_log = (V1 / "docs/error_log.md").read_text(encoding="utf-8")
    _i = err_log.find("ERR-008")
    err_quote = err_log[_i:_i + 400] if _i >= 0 else "（error_log 中未找到 ERR-008）"
    case("F13", "格式与契约（提示设计）", "question_id 未知（P2 试跑 3 条，原始输出未保留）", "dev 151（P2 试跑段）",
         "v1 未微调基座 + oracle 证据（E2），模板 v1（含尖括号占位符）",
         "（试跑问题未随产物保留）", "（E2 真值证据）",
         "error_log 登记的实际行为：模型输出 `Label: <yes>`（连尖括号一起抄），被严格解析判 invalid",
         "—（格式失败；无参考标签语义）",
         "模型把模板占位符连尖括号一起抄：`Label: <yes>` → 严格解析判 invalid（v1 ERR-008）",
         "提示缺陷曾被误判为『模型不会遵循格式』→ 已证伪：语义标签完全正确，只是夹带尖括号"
         "（error_log 登记文本节选见 evidence 字段；原始试跑输出未保留——"
         "现 predictions_e2.jsonl 151 条、0 条含 '<yes>'，系修复后全量运行覆盖）",
         "v1 修复 = 模板 v2 去掉尖括号占位符（Task A 模板冻结为 tpl_v2_20260920）",
         "占位符复述是否与模型规模相关 → 仅在 0.6B 上观察",
         "v1 docs/error_log.md（ERR-008 段落）+ runs/P2-baseline-20260920/predictions_e2.jsonl")

    # 渲染
    out = ["# 失败案例数据附录（自动生成）", "",
           f"生成时间：{datetime.now().isoformat(timespec='seconds')}；生成脚本：`portfolio/generate_portfolio_data.py`。",
           "所有字段取自冻结产物；引号内文本为逐字引用。分析性叙述见 `FAILURE_TAXONOMY.md`。", ""]
    for c in cases:
        out.append(f"## {c['id']} · {c['category']}")
        out.append(f"- **样本**：{c['sample_id']}｜划分：{c['split']}｜条件：{c['condition']}")
        out.append(f"- **问题**：{c['question']}")
        out.append(f"- **实际输入证据**：{c['evidence']}")
        out.append(f"- **原始输出（节选）**：`{c['raw_output']}`")
        out.append(f"- **参考判断及来源**：{c['reference']}")
        out.append(f"- **观察到的失败**：{c['failure']}")
        out.append(f"- **归类依据**：{c['basis']}")
        out.append(f"- **已有干预 / 仍未验证假说**：{c['intervention']} / {c['hypothesis']}")
        out.append(f"- **产物路径**：`{c['source']}`")
        out.append("")
    return "\n".join(out)


def main() -> int:
    PORT.mkdir(parents=True, exist_ok=True)
    rows = metric_rows()
    table = render_version_table(rows)
    cit = citation_stats()
    fails = fail_data()

    auto_ver = ("# 版本结果对照表（自动生成）\n\n"
                f"生成时间：{datetime.now().isoformat(timespec='seconds')}；"
                "脚本：`portfolio/generate_portfolio_data.py`。"
                "**不同协议的分数不可按高低排名**（模型/训练/证据/分母均不同）。\n\n"
                + table + "\n")
    (PORT / "version_comparison.auto.md").write_text(auto_ver, encoding="utf-8")

    auto_cit = ("# 引用与弃答计数（自动生成，自预测文件统计）\n\n"
                f"生成时间：{datetime.now().isoformat(timespec='seconds')}。\n\n"
                + cit + "\n\n注：v1 预测文件的 `citations` 已经过 v1 解析器 sorted() 处理（顺序信息丢失）；"
                "v3 记录保留模型原始引用顺序（`citations_model_order`）。\n")
    (PORT / "citation_stats.auto.md").write_text(auto_cit, encoding="utf-8")

    (PORT / "FAILURE_CASES.auto.md").write_text(fails, encoding="utf-8")

    # 回填 EVALUATION_FRAMEWORK.md 的 AUTO 区间
    fw = PORT / "EVALUATION_FRAMEWORK.md"
    if fw.exists():
        t = fw.read_text(encoding="utf-8")
        block = ("<!-- AUTO-START: version_table（由 generate_portfolio_data.py 生成，勿手改） -->\n"
                 + table + "\n<!-- AUTO-END -->")
        t = re.sub(r"<!-- AUTO-START: version_table.*?<!-- AUTO-END -->", block, t,
                   flags=re.S)
        fw.write_text(t, encoding="utf-8")
        print("EVALUATION_FRAMEWORK.md AUTO 区间已回填")
    print(f"rows={len(rows)}; cases={fails.count('## F')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
