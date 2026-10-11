#!/usr/bin/env python3
"""P6-3：Task B 评测（Label 指标 + 引用结构检查 + 人工审核包）。

## 三类检查，性质不同，必须分开报告

1. **Label 指标**（自动）：accuracy / macro-F1 / 逐类 recall。口径与 Task A 一致。
2. **引用结构检查**（自动）：只能检查「引用是否合法」，**不能检查「引用是否支持结论」**。
   * 合法：引用的编号在本次提供的证据范围内。
   * 非法（`invalid_citation`）：引用了不存在的编号 —— 最严重的失败模式。
   * 还要看：引用是否落在正确文献上（dev 可判定，因为知道 gold doc）。
3. **引用语义支持度**（**人工**）：引用是否真的支持那句话 —— 只能人工判断。
   本脚本只负责**导出审核包**，不代替人工结论。

## 口径纪律

* 任何契约违规（缺字段 / 引用越界）都计为**错误**（与 invalid 同等处理），
  不因为「Label 对了」就放过。这样「格式遵循率」才有意义。
* 违规的具体类型单独统计并随报告给出，信息不丢。

用法：
    python src/bioevidence/inference/eval_taskb.py --config configs/train_taskb.yaml
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from bioevidence.inference.prompts import build_evidence_block  # noqa: E402
from bioevidence.inference import prompts_taskb as tb  # noqa: E402
from bioevidence.evaluation.metrics import (  # noqa: E402
    ItemResult, compute_metrics, error_breakdown,
)
from bioevidence.retrieval.bm25_retriever import (  # noqa: E402
    build_retriever_from_chunks, index_config_from_yaml, load_chunks,
)


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/train_taskb.yaml")
    ap.add_argument("--data-config", default="configs/data.yaml")
    ap.add_argument("--eval-config", default="configs/eval.yaml")
    ap.add_argument("--m-evidence", type=int, default=3)
    ap.add_argument("--k-retrieve", type=int, default=10)
    ap.add_argument("--review-n-others", type=int, default=8,
                    help="人工审核包里除 maybe 之外额外抽取的样本数")
    ap.add_argument("--retrieval-condition", default="A0_bm25_baseline",
                    help="P7 检索条件名（configs/retrieval_section.yaml）")
    ap.add_argument("--out-suffix", default="",
                    help="输出文件名后缀，用于区分同一 adapter 在不同检索条件下的结果")
    ap.add_argument("--run-dir", default=None,
                    help="覆盖输出目录（默认用配置里的 out_dir）")
    ap.add_argument("--retrieval-file", default=None,
                    help="P8：预计算检索产物。提供时不再构造检索器。")
    ap.add_argument("--skip-review-packet", action="store_true",
                    help="跳过人工审核包导出（P7 的检索对照不需要重新生成审核包）")
    args = ap.parse_args()

    import yaml
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    cfg = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    data_cfg = yaml.safe_load((ROOT / args.data_config).read_text(encoding="utf-8"))
    eval_cfg = yaml.safe_load((ROOT / args.eval_config).read_text(encoding="utf-8"))
    ret_cfg = yaml.safe_load((ROOT / "configs/retrieval.yaml").read_text(encoding="utf-8"))

    proc = ROOT / data_cfg["paths"]["processed_dir"]
    man_dir = ROOT / data_cfg["paths"]["manifests_dir"]
    out_dir = ROOT / args.run_dir if args.run_dir else ROOT / cfg["run"]["out_dir"]
    adapter_dir = ROOT / cfg["run"]["adapter_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    version = data_cfg["dataset"]["version"]
    scheme = eval_cfg["split"]["scheme"]
    split = eval_cfg["split"]["split"]

    questions = {q["question_id"]: q for q in load_jsonl(proc / "questions.jsonl")}
    gold = {g["question_id"]: g["gold_label"] for g in load_jsonl(proc / "gold_labels.jsonl")}
    chunks = load_chunks(proc / "corpus_chunks.jsonl")
    chunk_by_id = {c["chunk_id"]: c for c in chunks}

    manifest = load_jsonl(man_dir / f"split_{version}.jsonl")
    qids = sorted(m["question_id"] for m in manifest
                  if m["scheme"] == scheme and m["split"] == split)

    model_path = str(ROOT / eval_cfg["model"]["path"])
    compute_dtype = (torch.bfloat16 if eval_cfg["model"]["precision"] == "bf16"
                     else torch.float16)
    quant = eval_cfg["model"]["quantization"]

    tok = AutoTokenizer.from_pretrained(model_path)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def count_tokens(t: str) -> int:
        return len(tok(t, add_special_tokens=False)["input_ids"])

    from bioevidence.retrieval.build_for_condition import build_retriever
    retriever, retriever_meta = build_retriever(args.retrieval_condition, chunks, ret_cfg)
    precomputed = None
    if args.retrieval_file:
        import types as _types
        _rows = [json.loads(l) for l in
                 (ROOT / args.retrieval_file).open(encoding="utf-8") if l.strip()]
        precomputed = {
            r["question_id"]: [_types.SimpleNamespace(**h) for h in r["retrieved"]]
            for r in _rows
        }
        retriever_meta = {**retriever_meta, "source": "precomputed_file",
                          "file": args.retrieval_file, "n_queries": len(precomputed)}
        print(f"[retrieval] condition={args.retrieval_condition} "
              f"precomputed={len(precomputed)} queries")

    t0 = time.time()
    base = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=quant["load_in_4bit"],
            bnb_4bit_quant_type=quant["bnb_4bit_quant_type"],
            bnb_4bit_use_double_quant=quant["bnb_4bit_use_double_quant"],
            bnb_4bit_compute_dtype=compute_dtype,
        ) if quant["load_in_4bit"] else None,
        device_map={"": 0})
    model = PeftModel.from_pretrained(base, str(adapter_dir))
    model.eval()
    load_seconds = round(time.time() - t0, 2)

    budget = int(eval_cfg["conditions"]["e2"]["evidence_token_budget"])
    # 解码预算优先取任务自己的配置：Task B 的输出比 Task A 长得多，
    # 沿用 Task A 的 48 会把四行输出截断（ERR-009）。
    dec = cfg.get("decoding") or eval_cfg["decoding"]
    max_new_tokens = int(dec["max_new_tokens"])
    print(f"[decoding] max_new_tokens={max_new_tokens} "
          f"(source={'configs/train_taskb.yaml' if cfg.get('decoding') else 'configs/eval.yaml'})")

    rows, items = [], []
    stats: Counter = Counter()
    t_start = time.time()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    for i, qid in enumerate(qids, start=1):
        q = questions[qid]
        hits = (precomputed[qid] if precomputed
                else retriever.search(q["question"], k=args.k_retrieve))
        top = hits[: args.m_evidence]
        selected = [chunk_by_id[h.chunk_id] for h in top]
        gold_doc = f"PMID{qid}"
        gold_doc_in = any(h.doc_id == gold_doc for h in top)
        block, emeta = build_evidence_block(selected, budget, count_tokens)
        n_ev = emeta["n_chunks_used"]
        ordered_ids = emeta["used_chunk_ids"]
        # 记录每个 E 编号对应的 doc，用于判断「引用是否落在正确文献上」
        idx_to_doc = {j + 1: chunk_by_id[cid]["doc_id"] for j, cid in enumerate(ordered_ids)}

        messages = tb.build_messages(q["question"], block)
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        inputs = tok(text, return_tensors="pt").to("cuda")
        n_input = int(inputs["input_ids"].shape[1])

        row = {"question_id": qid, "gold": gold[qid],
               "gold_answerable": "yes" if gold_doc_in else "no",
               "evidence_meta": emeta, "input_tokens": n_input,
               "idx_to_doc": {str(k): v for k, v in idx_to_doc.items()},
               "retrieved_doc_ids": [h.doc_id for h in top]}
        try:
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                                     do_sample=False, num_beams=1)
            torch.cuda.synchronize()
            raw = tok.decode(out[0][n_input:], skip_special_tokens=True)
            parsed = tb.parse_output(raw, n_evidence=n_ev)
            row.update({"raw_output": raw, **parsed.to_dict(), "error": None})
        except Exception as exc:  # noqa: BLE001
            row.update({"raw_output": None, "status": "invalid", "label": None,
                        "reason": None, "citations": [], "answerable": None,
                        "parse_note": "系统失败", "citation_issues": [],
                        "error": f"{type(exc).__name__}: {exc}"})
            stats["system_failure"] += 1

        # ---- 引用结构统计 ----
        if row["status"] == "invalid_citation":
            stats["invalid_citation"] += 1
        if row["status"] == "invalid":
            stats["invalid"] += 1
        if row["status"] != "invalid":
            stats["parsed"] += 1
            if row["answerable"] == "yes":
                stats["ans_yes"] += 1
                if row["citations"]:
                    stats["cited_when_answerable"] += 1
                    cited_docs = {idx_to_doc.get(c) for c in row["citations"]}
                    if gold_doc in cited_docs:
                        stats["citation_hits_gold_doc"] += 1
                else:
                    stats["no_citation_when_answerable"] += 1
            elif row["answerable"] == "no":
                stats["ans_no"] += 1
            if row["gold_answerable"] == "yes":
                stats["gold_answerable_yes"] += 1
                if row["answerable"] == "yes":
                    stats["answerable_correct"] += 1
            else:
                stats["gold_answerable_no"] += 1
                if row["answerable"] == "no":
                    stats["answerable_correct"] += 1

        # 口径：任何契约违规都计为错误
        usable = row["status"] == "ok"
        rows.append(row)
        items.append(ItemResult(
            qid, gold[qid],
            "ok" if usable else "invalid",
            row["label"] if usable else None,
        ))
        if i % 25 == 0 or i == len(qids):
            print(f"  [e7-taskb] {i}/{len(qids)}", flush=True)

    elapsed = time.time() - t_start
    write_jsonl(out_dir / f"predictions_e7_taskb{args.out_suffix}.jsonl", rows)

    m = compute_metrics(items)
    summary = m.to_dict()
    summary.update({
        "run_id": cfg["run"]["run_id"], "task": "taskB_structured_qa_with_citations",
        "adapter_dir": str(adapter_dir), "model_load_seconds": load_seconds,
        "elapsed_seconds": round(elapsed, 2),
        "seconds_per_item": round(elapsed / max(len(qids), 1), 3),
        "k_retrieved": args.k_retrieve, "m_evidence": args.m_evidence,
        "template_version": tb.TEMPLATE_VERSION,
        "template_fingerprint": tb.template_fingerprint(),
        "retrieval_condition": retriever_meta.get("condition"),
        "retrieval_file": args.retrieval_file,
        "retrieval_meta": retriever_meta,
        "errors": error_breakdown(items),
        "citation_structural_checks": {
            "note": (
                "以下只能检查引用的**合法性**；引用是否**支持**结论属于语义判断，"
                "必须人工审核（见 review_packet）。"
            ),
            "parsed_outputs": stats["parsed"],
            "invalid_format": stats["invalid"],
            "invalid_citation_out_of_range": stats["invalid_citation"],
            "cited_rate_when_answerable_yes": (
                round(stats["cited_when_answerable"] / max(stats["ans_yes"], 1), 4)
                if stats["ans_yes"] else None),
            "no_citation_when_answerable_yes": stats["no_citation_when_answerable"],
            "citation_points_to_gold_document_rate": (
                round(stats["citation_hits_gold_doc"] / max(stats["cited_when_answerable"], 1), 4)
                if stats["cited_when_answerable"] else None),
            "answerable_distribution": {
                "predicted_yes": stats["ans_yes"], "predicted_no": stats["ans_no"],
            },
            "answerable_accuracy": (
                round(stats["answerable_correct"]
                      / max(stats["gold_answerable_yes"] + stats["gold_answerable_no"], 1), 4)),
            "gold_answerable_distribution": {
                "yes": stats["gold_answerable_yes"], "no": stats["gold_answerable_no"],
                "definition": "gold answerable = 检索到的 m 条证据里是否包含问题所属文献",
            },
        },
        "scoring_policy": (
            "任何契约违规（缺字段 / 引用越界）都计为错误，不因 Label 正确而豁免；"
            "违规类型在 citation_structural_checks 中单独统计。"
        ),
    })
    if torch.cuda.is_available():
        summary["peak_memory_gb"] = {
            "allocated": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
            "reserved": round(torch.cuda.max_memory_reserved() / 1024**3, 3),
        }
    (out_dir / f"metrics_e7_taskb{args.out_suffix}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------- 人工审核包 ----------------
    if args.skip_review_packet:
        print("[skip] --skip-review-packet：不重新生成人工审核包")
        print(f"[E7] acc={m.accuracy} macro_f1={m.macro_f1} invalid={m.n_invalid} "
              f"failure={m.n_failure} ({elapsed:.1f}s)")
        for lab in ("yes", "no", "maybe"):
            v = m.per_class[lab]
            print(f"  {lab:6} P={v['precision']} R={v['recall']} F1={v['f1']}")
        cs = summary["citation_structural_checks"]
        print(f"  citations: invalid_out_of_range={cs['invalid_citation_out_of_range']} "
              f"cited_rate={cs['cited_rate_when_answerable_yes']} "
              f"points_to_gold_doc={cs['citation_points_to_gold_document_rate']}")
        print(f"  answerable: pred={cs['answerable_distribution']} "
              f"gold={cs['gold_answerable_distribution']} acc={cs['answerable_accuracy']}")
        return 0
    review_dir = ROOT / data_cfg["paths"]["review_dir"] if "review_dir" in data_cfg["paths"] \
        else ROOT / "data" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    meta = json.loads((man_dir / f"dataset_meta_{version}.json").read_text(encoding="utf-8"))
    disc_ids = {r["doc_id"].replace("PMID", "")
                for r in meta["audit"]["task_validity"]["discussion_family_records"]}

    maybe_rows = [r for r in rows if r["gold"] == "maybe"]
    others = [r for r in rows if r["gold"] != "maybe"]
    others_sorted = sorted(others, key=lambda r: (r["gold"], r["question_id"]))
    step = max(len(others_sorted) // max(args.review_n_others, 1), 1)
    sampled_others = others_sorted[::step][: args.review_n_others]

    packet = maybe_rows + sampled_others
    review_rows = []
    for r in packet:
        qi = r["question_id"]
        review_rows.append({
            "review_id": f"R{len(review_rows)+1:03d}",
            "question_id": qi,
            "must_review": "YES" if r["gold"] == "maybe" else "no",
            "in_dev_split": "yes",
            "evidence_has_discussion_family_section": "yes" if qi in disc_ids else "no",
            "question": questions[qi]["question"],
            "gold_label": r["gold"],
            "model_label": r["label"] if r["status"] == "ok" else f"<{r['status']}>",
            "model_answerable": r["answerable"],
            "gold_answerable": r["gold_answerable"],
            "model_citations": ",".join(f"E{c}" for c in r["citations"]),
            "cited_docs": ";".join(sorted({r["idx_to_doc"].get(str(c), "?")
                                           for c in r["citations"]})),
            "gold_source_doc": f"PMID{qi}",
            "evidence_block": "\n".join(
                f"[E{j+1}] ({chunk_by_id[cid]['section']}) {chunk_by_id[cid]['text']}"
                for j, cid in enumerate(r["evidence_meta"]["used_chunk_ids"])),
            "model_reason": r["reason"],
            "model_raw_output": r["raw_output"],
            # ---- 以下由项目负责人填写 ----
            "REVIEW_证据是否支持该结论": "",
            "REVIEW_引用是否真的支撑理由": "",
            "REVIEW_maybe判定是否合理": "",
            "REVIEW_备注": "",
        })

    csv_path = review_dir / "review_packet_taskb_dev.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(review_rows[0]))
        writer.writeheader()
        for rr in review_rows:
            writer.writerow(rr)

    md_lines = [
        "# Task B 人工审核包（dev 151 条中的抽样）",
        "",
        "> **审核人：项目负责人本人。无独立第二审核者，不计算审核者间一致性。**",
        "> 请在审核记录里保持这一披露，不要把结论表述为「双人复核」或「专家一致性」。",
        "",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat()}",
        f"- 样本数：{len(review_rows)}（其中 dev 中全部 `maybe` 样本 {len(maybe_rows)} 条为**必审**）",
        f"- CSV（可填表）：`{csv_path.name}`",
        "- 用途：判断 ① 证据是否支持模型给出的结论；② 引用是否真的支撑它写的理由；"
        "③ `maybe` 的判定是否合理。",
        "",
        "## 审核提示",
        "",
        "- 本包刻意**覆盖 P1 抽查发现的三种情形**（在表格 `evidence_has_discussion_family_section` 列标注）：",
        "  1. 证据里有 DISCUSSION/LIMITATIONS/FINDINGS 类章节 —— 结论方向可能可直接读出；",
        "  2. 结论有条件限定（如「仅在亚组中显著」）；",
        "  3. 问句本身不是二值问题。",
        "- 引用检查分两层：**合法性**（编号是否存在）已自动完成；"
        "**语义支持**（引用内容是否真的支撑那句话）需要你判断。",
        "",
        "---",
        "",
    ]
    for rr in review_rows:
        md_lines += [
            f"## {rr['review_id']}｜PMID {rr['question_id']}"
            f"（{'必审' if rr['must_review'] == 'YES' else '抽审'}）",
            "",
            f"- 讨论类章节：{rr['evidence_has_discussion_family_section']}",
            f"- gold 标签：`{rr['gold_label']}`｜模型标签：`{rr['model_label']}`",
            f"- gold answerable：`{rr['gold_answerable']}`｜模型 answerable：`{rr['model_answerable']}`",
            f"- 模型引用：`{rr['model_citations']}`"
            f"（对应文献：{rr['cited_docs'] or '—'}；正确文献：{rr['gold_source_doc']}）",
            "",
            f"**问题**：{rr['question']}",
            "",
            "**提供的证据**：",
            "",
            "```text",
            rr["evidence_block"],
            "```",
            "",
            f"**模型理由**：{rr['model_reason']}",
            "",
            "<details><summary>模型原始输出</summary>",
            "",
            "```text",
            (rr["model_raw_output"] or "").strip(),
            "```",
            "",
            "</details>",
            "",
            "**待填**：",
            "- 证据是否支持该结论：",
            "- 引用是否真的支撑理由：",
            "- maybe 判定是否合理：",
            "- 备注：",
            "",
            "---",
            "",
        ]
    (review_dir / "review_packet_taskb_dev.md").write_text(
        "\n".join(md_lines), encoding="utf-8")

    packet_summary = {
        "n_items": len(review_rows),
        "n_must_review_maybe": len(maybe_rows),
        "n_sampled_others": len(sampled_others),
        "n_with_discussion_family_section": sum(
            1 for r in review_rows if r["evidence_has_discussion_family_section"] == "yes"),
        "reviewer": "项目负责人本人（单人审核，无独立第二审核者）",
        "files": {
            "csv": str(csv_path.relative_to(ROOT)),
            "markdown": str((review_dir / "review_packet_taskb_dev.md").relative_to(ROOT)),
        },
        "status": "pending_human_review",
        "disclosure": (
            "人工审核尚未完成。完成后必须披露「单人审核、独立性有限、"
            "未计算审核者间一致性」，不得表述为双人复核或专家一致性。"
        ),
    }
    (out_dir / "review_packet_summary.json").write_text(
        json.dumps(packet_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[E7] acc={m.accuracy} macro_f1={m.macro_f1} invalid={m.n_invalid} "
          f"failure={m.n_failure} ({elapsed:.1f}s)")
    for lab in ("yes", "no", "maybe"):
        v = m.per_class[lab]
        print(f"  {lab:6} P={v['precision']} R={v['recall']} F1={v['f1']}")
    cs = summary["citation_structural_checks"]
    print(f"  citations: invalid_out_of_range={cs['invalid_citation_out_of_range']} "
          f"cited_rate={cs['cited_rate_when_answerable_yes']} "
          f"points_to_gold_doc={cs['citation_points_to_gold_document_rate']}")
    print(f"  answerable: pred={cs['answerable_distribution']} "
          f"gold={cs['gold_answerable_distribution']} acc={cs['answerable_accuracy']}")
    print(f"[review packet] {len(review_rows)} items -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
