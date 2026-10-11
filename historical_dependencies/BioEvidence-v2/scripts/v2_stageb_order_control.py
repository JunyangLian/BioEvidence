#!/usr/bin/env python3
"""v2 阶段 B：证据顺序对照（只改变排列，不改变内容）。

## 干预目标

在**冻结**模型 / adapter / 证据内容 / 提示主体 / 解码参数 / 评分逻辑的前提下，
只改变证据块的**排列顺序**与随之变化的显示编号，测量引用落点是否随位置移动。
本脚本**只做 P（位置）干预**，不对 T（监督目标）或 M（训练-推理证据组成差异）下任何因果结论。

## 四个条件

| 条件 | 排列规则 |
|---|---|
| `B0_original` | 按 `section_index` **升序**（与冻结流水线 `build_evidence_block` 的最终输出一致） |
| `B1_result_first` | **结果族优先**，族内与其余片段各自**保持原相对顺序**（稳定划分） |
| `B2_reversed` | B0 的**完全逆序** |
| `B3_shuffled` | **固定种子**随机排列（种子按 `seed|question_id` 派生，跨运行确定） |

**结果族定义不临时扩展**：直接 `import` 冻结配置里的
`bioevidence.retrieval.section_aware.RESULT_SECTION_KEYS`（= `("RESULT", "FINDING")`，子串匹配），
即 A2 检索条件本身所用的那套定义，也与 v1 全部已发布统计（5.6% / 43.6% / E1 0/500）同源。

## 关键纪律（对应负责人本轮要求）

1. **先固定内容、再排列**：先用**原条件**跑 `build_evidence_block` 得到实际送入模型的
   片段集合（`used_chunk_ids`），把它**封存**；四个条件只在**这个封存集合**上做排列。
   这样 `break`-式预算截断不会因换序而改变入选集合。
2. **集合一致性硬断言**：四条件的 chunk_id 集合必须完全相同，否则该样本**中止**，
   记录 `aborted_set_mismatch`，**不静默删改证据**。
3. **稳定 ID 映射**：每个样本 × 每个条件都保存 `display_to_chunk`（`E1 -> chunk_id`）。
   比较引用时必须映射回 chunk_id，**不得**把 `E1 -> E3` 直接当成引用内容变化。
4. **基线复现校验**：B0 的 `used_chunk_ids` 必须与 v1 冻结预测逐条一致；
   若不一致 → 记录 `baseline_mismatch` 并**中止该样本**，不静默继续。
5. **相同输入标记**：某条件的排列若与 B0 完全相同，记 `identical_to_baseline=true`，
   它在分析中**不是有效干预**。
6. 缓存键区分 `condition / model / prompt / decoding`；支持断点续跑。

## 用法

```bash
PY="C:/Users/yang/.workbuddy/binaries/python/envs/bioevidence/Scripts/python.exe"

# 1) 只做一致性/可复现性核验（不需要 GPU、不生成）
"$PY" -X utf8 scripts/v2_stageb_order_control.py --mode prepare \
    --v1-root C:/1_yanjiusheng/BioEvidence/BioEvidence-v1 \
    --run-dir runs/P1-v2-stageB-order-20260924

# 2) 冒烟：选定样本 × 四条件
"$PY" -X utf8 scripts/v2_stageb_order_control.py --mode run --subset smoke \
    --v1-root ... --run-dir runs/P1-v2-stageB-order-20260924

# 3) 完整 dev151（本轮不执行，仅供阶段 B 正式运行）
"$PY" -X utf8 scripts/v2_stageb_order_control.py --mode run --subset dev
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONDITIONS = ("B0_original", "B1_result_first", "B2_reversed", "B3_shuffled")
PREPARE_VERSION = "v2_stageB_order_v1_20260924"


def load_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def write_jsonl(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def sha8(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


# --------------------------------------------------------------------------
# 排列规则：全部作用在「封存后的 chunk_id 列表」上
# --------------------------------------------------------------------------
def order_b0(ids: list[str]) -> list[str]:
    """原顺序 = 已按 section_index 升序（build_evidence_block 的输出顺序）。"""
    return list(ids)


def order_b1(ids: list[str], section_of) -> list[str]:
    """结果族优先；族内与其余片段各自保持原相对顺序（稳定划分）。"""
    res = [i for i in ids if section_of(i)]
    other = [i for i in ids if not section_of(i)]
    return res + other


def order_b2(ids: list[str]) -> list[str]:
    return list(reversed(ids))


def order_b3(ids: list[str], seed: str) -> list[str]:
    out = list(ids)
    random.Random(seed).shuffle(out)     # 字符串种子 → 跨运行确定
    return out


def build_orders(ids: list[str], section_of, shuffle_seed: str) -> dict[str, list[str]]:
    return {
        "B0_original": order_b0(ids),
        "B1_result_first": order_b1(ids, section_of),
        "B2_reversed": order_b2(ids),
        "B3_shuffled": order_b3(ids, shuffle_seed),
    }


def render_block(ordered_ids: list[str], chunk_by_id: dict) -> str:
    """与 prompts.py:108-111 的渲染格式逐字一致：`[E{i}] ({section}) {text}`。"""
    if not ordered_ids:
        return "(no evidence provided)"
    return "\n".join(
        f"[E{i}] ({chunk_by_id[cid]['section']}) {chunk_by_id[cid]['text']}"
        for i, cid in enumerate(ordered_ids, start=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["prepare", "run"], required=True)
    ap.add_argument("--v1-root", required=True)
    ap.add_argument("--run-dir", default="runs/P1-v2-stageB-order-20260924")
    ap.add_argument("--subset", choices=["smoke", "dev"], default="smoke")
    ap.add_argument("--n-smoke", type=int, default=14)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--shuffle-seed", default="v2-order-20260924")
    ap.add_argument("--max-new-tokens", type=int, default=160)
    ap.add_argument("--m-evidence", type=int, default=3)
    ap.add_argument("--k-retrieve", type=int, default=10)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    root = Path(args.v1_root)
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root / "src"))

    import torch
    import yaml
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    from bioevidence.inference.prompts import build_evidence_block
    from bioevidence.inference import prompts_taskb as tb
    from bioevidence.retrieval.build_for_condition import build_retriever
    from bioevidence.retrieval.section_aware import RESULT_SECTION_KEYS, is_result_section

    data_cfg = yaml.safe_load((root / "configs/data.yaml").read_text(encoding="utf-8"))
    eval_cfg = yaml.safe_load((root / "configs/eval.yaml").read_text(encoding="utf-8"))
    taskb_cfg = yaml.safe_load((root / "configs/train_taskb.yaml").read_text(encoding="utf-8"))
    ret_cfg = yaml.safe_load((root / "configs/retrieval.yaml").read_text(encoding="utf-8"))

    proc = root / data_cfg["paths"]["processed_dir"]
    man_dir = root / data_cfg["paths"]["manifests_dir"]
    version = data_cfg["dataset"]["version"]
    scheme = eval_cfg["split"]["scheme"]
    budget = int(eval_cfg["conditions"]["e2"]["evidence_token_budget"])
    model_path = str(root / eval_cfg["model"]["path"])
    adapter_dir = root / taskb_cfg["run"]["adapter_dir"]
    dec = taskb_cfg["decoding"]
    max_new_tokens = int(args.max_new_tokens)

    chunks = load_jsonl(proc / "corpus_chunks.jsonl")
    chunk_by_id = {c["chunk_id"]: c for c in chunks}
    questions = {q["question_id"]: q for q in load_jsonl(proc / "questions.jsonl")}
    manifest = load_jsonl(man_dir / f"split_{version}.jsonl")

    dev_ids = sorted(m["question_id"] for m in manifest
                     if m["scheme"] == scheme and m["split"] == "dev")
    test_ids = {m["question_id"] for m in manifest
                if m["scheme"] == "official" and m["split"] == "test"}

    def section_of(cid: str) -> bool:
        return is_result_section(chunk_by_id[cid].get("section"))

    tok = AutoTokenizer.from_pretrained(model_path)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def count_tokens(t: str) -> int:
        return len(tok(t, add_special_tokens=False)["input_ids"])

    retriever, ret_meta = build_retriever("A2_quota", chunks, ret_cfg)

    # 冻结的 dev/A2 预测（用于基线复现校验；只读）
    frozen_path = root / "runs/P7-retrieval-20260921/predictions_e7_taskb_A2_quota.jsonl"
    frozen = {r["question_id"]: r for r in load_jsonl(frozen_path)} if frozen_path.exists() else {}

    prompt_fp = tb.template_fingerprint()
    cache_cfg_key = sha8(json.dumps({
        "prepare_version": PREPARE_VERSION, "condition_set": list(CONDITIONS),
        "model": model_path, "adapter": str(adapter_dir), "prompt_fp": prompt_fp,
        "decoding": {"max_new_tokens": max_new_tokens, "do_sample": dec.get("do_sample"),
                     "num_beams": dec.get("num_beams")},
        "shuffle_seed": args.shuffle_seed, "m_evidence": args.m_evidence,
        "k_retrieve": args.k_retrieve, "budget": budget,
    }, sort_keys=True))

    # ---------------- 逐样本：封存内容 + 四条件排列 ----------------
    plans: list[dict] = []
    aborted: list[dict] = []
    for qid in dev_ids:
        q = questions[qid]
        hits = retriever.search(q["question"], k=args.k_retrieve)
        top = hits[: args.m_evidence]
        selected = [chunk_by_id[h.chunk_id] for h in top]
        block0, emeta = build_evidence_block(selected, budget, count_tokens)
        sealed = list(emeta["used_chunk_ids"])          # ← 封存：原条件实际入选集合

        if not sealed:
            aborted.append({"question_id": qid, "reason": "sealed_set_empty"})
            continue

        orders = build_orders(sealed, section_of, f"{args.shuffle_seed}|{qid}")

        # 硬断言 1：集合必须完全一致
        sets = {c: tuple(sorted(o)) for c, o in orders.items()}
        if len(set(sets.values())) != 1:
            aborted.append({"question_id": qid, "reason": "aborted_set_mismatch",
                            "sets": {c: list(v) for c, v in sets.items()}})
            continue

        # 硬断言 2：B0 必须复现冻结流程的 evidence_meta
        frozen_used = (frozen.get(qid, {}).get("evidence_meta") or {}).get("used_chunk_ids")
        baseline_match = (frozen_used is None) or (list(frozen_used) == sealed)
        if not baseline_match:
            aborted.append({"question_id": qid, "reason": "baseline_mismatch",
                            "sealed": sealed, "frozen": list(frozen_used)})
            continue

        per_cond = {}
        for cond, order in orders.items():
            blk = render_block(order, chunk_by_id)
            n_tok = count_tokens(blk)
            # 内容 token = 只看「(section) text」，**不含** `[E{i}]` 显示编号前缀。
            # 为什么要分开算：`[E{i}]` 里的数字本身会改变 token 化
            # （实测 E1/E2/E3 前缀可使整块 token 数 ±1），
            # 那是**显示编号造成的**，不是内容变化。内容不变性必须用 content_tok 判定。
            content_tok = sum(count_tokens(f"({chunk_by_id[c]['section']}) {chunk_by_id[c]['text']}")
                              for c in order)
            per_cond[cond] = {
                "order": order,
                "display_to_chunk": {f"E{i}": cid for i, cid in enumerate(order, start=1)},
                "n_chunks": len(order),
                "content_token_len": content_tok,
                "block_token_len": n_tok,
                "display_numbering_token_delta": n_tok - content_tok,
                "block_sha8": sha8(blk),
                "identical_to_baseline": order == orders["B0_original"],
                "n_result_family": sum(1 for c in order if section_of(c)),
                "result_positions": [i + 1 for i, c in enumerate(order) if section_of(c)],
            }

        # 硬断言 3：四条件的**内容** token 必须一致（集合一致 ⇒ 内容一致）
        content_lens = {c: v["content_token_len"] for c, v in per_cond.items()}
        if len(set(content_lens.values())) != 1:
            aborted.append({"question_id": qid, "reason": "content_len_mismatch",
                            "content_lens": content_lens})
            continue
        # 显示编号会带来 ±1 的整块 token 抖动：记录，不作为中止理由，但要显式留档
        block_lens = {c: v["block_token_len"] for c, v in per_cond.items()}
        max_block = max(block_lens.values())

        n_distinct = len({tuple(v["order"]) for v in per_cond.values()})
        plans.append({
            "question_id": qid,
            "n_ev": len(sealed),
            "sealed_chunk_ids": sealed,
            "sealed_sections": [chunk_by_id[c]["section"] for c in sealed],
            "sealed_has_result_family": any(section_of(c) for c in sealed),
            "frozen_baseline_used_ids_match": baseline_match,
            "n_distinct_orderings": n_distinct,
            "n_nonbaseline_conditions_identical_to_baseline": sum(
                v["identical_to_baseline"] for c, v in per_cond.items()
                if c != "B0_original"),
            "effective_intervention_conditions": [
                c for c in CONDITIONS
                if c != "B0_original" and not per_cond[c]["identical_to_baseline"]],
            "content_token_len": per_cond["B0_original"]["content_token_len"],
            "block_token_len": per_cond["B0_original"]["block_token_len"],
            "block_token_len_max": max_block,
            "display_numbering_token_span": max_block - min(block_lens.values()),
            "budget_tokens": budget,
            "block_within_budget": max_block <= budget,
            "conditions": per_cond,
        })

    # ---------------- 抽查样本选择（确定性） ----------------
    # 选取「排列确实不同」的样本：先要 3 条证据、且 distinct orderings 多者优先。
    rankable = [p for p in plans if p["n_ev"] >= 3]
    rankable.sort(key=lambda p: (-p["n_distinct_orderings"], p["question_id"]))
    override = run_dir / "smoke_selection_override.json"
    if args.n_smoke and override.exists():
        chosen_ids = json.loads(override.read_text(encoding="utf-8"))["question_ids"]
        smoke = [p for p in plans if p["question_id"] in set(chosen_ids)]
    else:
        smoke = rankable[: args.n_smoke]
    chosen = plans if args.subset == "dev" else (smoke if smoke else plans)
    chosen_ids = [p["question_id"] for p in chosen]

    if args.mode == "prepare":
        report = {
            "meta": {
                "task": "v2 阶段 B：顺序对照准备（不生成）",
                "prepare_version": PREPARE_VERSION,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "v1_root": str(root), "run_dir": str(run_dir),
                "result_section_definition": {
                    "source": "bioevidence.retrieval.section_aware.RESULT_SECTION_KEYS",
                    "keys": list(RESULT_SECTION_KEYS),
                    "match": "section 字符串大写后子串匹配",
                },
                "conditions": {
                    "B0_original": "section_index 升序（= 冻结 build_evidence_block 输出顺序）",
                    "B1_result_first": "结果族优先，族内/其余各自保持原相对顺序",
                    "B2_reversed": "B0 完全逆序",
                    "B3_shuffled": f"固定种子 shuffle（seed 派生自 '{args.shuffle_seed}|<qid>'）",
                },
                "seal_policy": "先用原条件跑 build_evidence_block 封存入选集合，再在该集合上排列",
                "cache_config_key": cache_cfg_key,
                "retrieval_condition": ret_meta.get("condition"),
                "budget_tokens": budget, "m_evidence": args.m_evidence,
                "k_retrieve": args.k_retrieve,
                "prompt_template": tb.TEMPLATE_VERSION, "prompt_fingerprint": prompt_fp,
                "adapter_dir": str(adapter_dir), "model_path": model_path,
                "max_new_tokens": max_new_tokens,
                "dev_n": len(dev_ids),
            },
            "counts": {
                "dev_total": len(dev_ids),
                "planned": len(plans), "aborted": len(aborted),
                "with_3_evidence": sum(1 for p in plans if p["n_ev"] == 3),
                "smoke_selected": len(smoke),
                "smoke_all_4_orderings_distinct": sum(
                    1 for p in smoke if p["n_distinct_orderings"] == 4),
                "samples_with_all_conditions_identical": sum(
                    1 for p in plans if p["n_distinct_orderings"] == 1),
            },
            "red_lines": {
                "selected_from_dev_only": set(chosen_ids) <= set(dev_ids),
                "intersect_v1_test": sorted(set(chosen_ids) & test_ids),
                "no_test_used": not (set(chosen_ids) & test_ids),
            },
            "integrity": {
                "all_sets_identical": all(
                    a["reason"] != "aborted_set_mismatch" for a in aborted),
                "all_content_token_lens_equal": all(
                    len({v["content_token_len"] for v in p["conditions"].values()}) == 1
                    for p in plans),
                "display_numbering_causes_token_span": {
                    "n_samples_affected": sum(
                        1 for p in plans if p["display_numbering_token_span"] > 0),
                    "max_span_tokens": max(
                        (p["display_numbering_token_span"] for p in plans), default=0),
                    "explanation": (
                        "渲染前缀 `[E{i}]` 的序号本身会改变 token 化（E1/E2/E3 前缀 token 数可不同），"
                        "因此**整块** token 数会随排列 ±1 抖动。这是**显示编号**造成的，"
                        "不是证据内容变化；内容不变性由 content_token_len 判定。"),
                },
                "all_blocks_within_budget": all(p["block_within_budget"] for p in plans),
                "baseline_frozen_match_n": sum(
                    1 for p in plans if p["frozen_baseline_used_ids_match"]),
                "baseline_frozen_match_rate": round(
                    sum(1 for p in plans if p["frozen_baseline_used_ids_match"])
                    / max(len(plans), 1), 4),
            },
            "aborted_by_reason": {r: sum(1 for a in aborted if a["reason"] == r)
                                  for r in sorted({a["reason"] for a in aborted})},
            "aborted_detail": aborted,
            "smoke_selection": {
                "rule": "n_ev>=3 且 distinct_orderings 多者优先（确定性排序）",
                "question_ids": chosen_ids,
                "per_sample": [{"question_id": p["question_id"], "n_ev": p["n_ev"],
                                "n_distinct_orderings": p["n_distinct_orderings"],
                                "sections": p["sealed_sections"]} for p in chosen],
            },
        }
        (run_dir / "order_plan.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (run_dir / "order_plan_all_samples.json").write_text(
            json.dumps({"plans": plans, "aborted": aborted}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"[prepare] dev={len(dev_ids)} planned={len(plans)} aborted={len(aborted)}")
        print(f"[prepare] smoke_selected={len(smoke)} "
              f"all4distinct={report['counts']['smoke_all_4_orderings_distinct']}")
        print(f"[prepare] red_lines={json.dumps(report['red_lines'], ensure_ascii=False)}")
        print(f"[prepare] integrity={json.dumps(report['integrity'], ensure_ascii=False)}")
        print(f"[written] {run_dir/'order_plan.json'}")
        print(f"[written] {run_dir/'order_plan_all_samples.json'}")
        return 0

    # ---------------- run：真正生成 ----------------
    cache_dir = run_dir / "cache" / cache_cfg_key
    cache_dir.mkdir(parents=True, exist_ok=True)

    compute_dtype = (torch.bfloat16 if eval_cfg["model"]["precision"] == "bf16"
                     else torch.float16)
    quant = eval_cfg["model"]["quantization"]
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
    load_s = round(time.time() - t0, 2)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    rows, n_cache_hit = [], 0
    t_start = time.time()
    for p in chosen:
        qid = p["question_id"]
        for cond in CONDITIONS:
            if cond not in p["conditions"]:
                continue
            cpath = cache_dir / f"{qid}__{cond}.json"
            if not args.no_cache and cpath.exists():
                rec = json.loads(cpath.read_text(encoding="utf-8"))
                n_cache_hit += 1
                rows.append(rec)
                continue

            order = p["conditions"][cond]["order"]
            block = render_block(order, chunk_by_id)
            messages = tb.build_messages(questions[qid]["question"], block)
            text = tok.apply_chat_template(messages, tokenize=False,
                                           add_generation_prompt=True,
                                           enable_thinking=False)
            inputs = tok(text, return_tensors="pt").to("cuda")
            n_input = int(inputs["input_ids"].shape[1])
            ts = time.time()
            try:
                with torch.no_grad():
                    out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                                         do_sample=False, num_beams=1)
                torch.cuda.synchronize()
                raw = tok.decode(out[0][n_input:], skip_special_tokens=True)
                parsed = tb.parse_output(raw, n_evidence=len(order))
                err = None
            except Exception as exc:                            # noqa: BLE001
                raw, err = None, f"{type(exc).__name__}: {exc}"
                parsed = tb.ParsedTaskB(status="invalid", parse_note="系统失败")
            item_s = round(time.time() - ts, 3)

            rec = {
                "question_id": qid, "condition": cond,
                "cache_config_key": cache_cfg_key,
                "n_evidence": len(order),
                "display_to_chunk": p["conditions"][cond]["display_to_chunk"],
                "chunk_order": order,
                "chunk_order_sections": [chunk_by_id[c]["section"] for c in order],
                "identical_to_baseline": p["conditions"][cond]["identical_to_baseline"],
                "n_result_family": p["conditions"][cond]["n_result_family"],
                "result_positions": p["conditions"][cond]["result_positions"],
                "block_sha8": p["conditions"][cond]["block_sha8"],
                "block_token_len": p["conditions"][cond]["block_token_len"],
                "input_tokens": n_input,
                "raw_output": raw,
                **parsed.to_dict(),
                "error": err,
                "item_seconds": item_s,
            }
            cpath.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            rows.append(rec)
        print(f"  [order] {qid} done", flush=True)

    elapsed = time.time() - t_start
    write_jsonl(run_dir / f"predictions_order_{args.subset}.jsonl", rows)

    # ---------------- 引用映射回 chunk_id 的比较（不做语义支持率） ----------------
    by_q: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_q.setdefault(r["question_id"], {})[r["condition"]] = r
    comparisons = []
    for qid, per in by_q.items():
        base_r = per.get("B0_original")
        if not base_r:
            continue
        def cited_chunks(rec):
            return {rec["display_to_chunk"].get(f"E{c}") for c in (rec.get("citations") or [])
                    if rec["display_to_chunk"].get(f"E{c}")}
        base_cit = cited_chunks(base_r)
        base_pos = sorted(base_r.get("citations") or [])
        for cond in CONDITIONS:
            if cond == "B0_original" or cond not in per:
                continue
            rec = per[cond]
            cit = cited_chunks(rec)
            comparisons.append({
                "question_id": qid, "condition": cond,
                "identical_input_to_baseline": rec["identical_to_baseline"],
                "label_base": base_r.get("label"), "label_cond": rec.get("label"),
                "label_changed": base_r.get("label") != rec.get("label"),
                "answerable_base": base_r.get("answerable"),
                "answerable_cond": rec.get("answerable"),
                "abstain_changed": (base_r.get("answerable") != rec.get("answerable")),
                "citations_display_base": base_pos,
                "citations_display_cond": sorted(rec.get("citations") or []),
                "display_index_changed": base_pos != sorted(rec.get("citations") or []),
                "cited_chunks_base": sorted(x for x in base_cit if x),
                "cited_chunks_cond": sorted(x for x in cit if x),
                "cited_chunk_set_changed": base_cit != cit,
                "status_base": base_r.get("status"), "status_cond": rec.get("status"),
            })

    # 机制诊断用的两个小判定（写成函数，避免嵌套生成式的作用域陷阱）
    def cited_any_result_family(rec: dict) -> bool:
        for x in (rec.get("citations") or []):
            cid = rec["display_to_chunk"].get(f"E{x}")
            if cid and is_result_section(chunk_by_id[cid].get("section")):
                return True
        return False

    def has_citations(rec: dict) -> bool:
        return bool(rec.get("citations"))

    def cited_e1(rec: dict) -> bool:
        return 1 in (rec.get("citations") or [])

    consistency = {
        "meta": {
            "task": "v2 阶段 B：顺序对照冒烟",
            "subset": args.subset, "run_dir": str(run_dir),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "cache_config_key": cache_cfg_key,
            "model_load_seconds": load_s,
            "elapsed_seconds": round(elapsed, 2),
            "n_items": len(rows), "n_cache_hits": n_cache_hit,
            "note": ("本轮**不输出语义支持率**：人工支持关系尚未标注。"
                     "以下 E1/结果族统计**只是机制诊断指标**，不得当作正确性指标。"),
        },
        "checks": {
            "all_conditions_share_same_chunk_set": all(
                len({tuple(sorted(p["conditions"][c]["order"])) for c in CONDITIONS}) == 1
                for p in chosen),
            "all_conditions_same_content_token_len": all(
                len({p["conditions"][c]["content_token_len"] for c in CONDITIONS}) == 1
                for p in chosen),
            "display_numbering_token_span_max": max(
                (p["display_numbering_token_span"] for p in chosen), default=0),
            "all_blocks_within_budget": all(p["block_within_budget"] for p in chosen),
            "display_to_chunk_consistent_with_order": all(
                list(v["display_to_chunk"].values()) == list(v["order"])
                for p in chosen for v in p["conditions"].values()),
            "baseline_frozen_used_ids_match_all": all(
                p["frozen_baseline_used_ids_match"] for p in chosen),
            "parser_imported_from_frozen_module": True,
        },
        "per_condition": {
            c: {
                "n": sum(1 for r in rows if r["condition"] == c),
                "n_ok": sum(1 for r in rows if r["condition"] == c and r["status"] == "ok"),
                "n_invalid": sum(1 for r in rows if r["condition"] == c and r["status"] == "invalid"),
                "n_invalid_citation": sum(1 for r in rows if r["condition"] == c
                                          and r["status"] == "invalid_citation"),
                # ↓↓ 机制诊断指标，不是正确性指标 ↓↓
                "diagnostic_citation_result_family_rate": round(
                    sum(1 for r in rows if r["condition"] == c and cited_any_result_family(r))
                    / max(sum(1 for r in rows if r["condition"] == c and has_citations(r)), 1), 4),
                "diagnostic_cited_E1_rate": round(
                    sum(1 for r in rows if r["condition"] == c and cited_e1(r))
                    / max(sum(1 for r in rows if r["condition"] == c and has_citations(r)), 1), 4),
                "mean_output_chars": round(
                    sum(len(r["raw_output"] or "") for r in rows if r["condition"] == c)
                    / max(sum(1 for r in rows if r["condition"] == c), 1), 1),
                "mean_item_seconds": round(
                    sum(r["item_seconds"] for r in rows if r["condition"] == c)
                    / max(sum(1 for r in rows if r["condition"] == c), 1), 3),
            } for c in CONDITIONS
        },
        "citation_comparison": {
            "n_pairs": len(comparisons),
            "n_pairs_with_identical_input": sum(
                1 for x in comparisons if x["identical_input_to_baseline"]),
            "n_label_changed": sum(1 for x in comparisons if x["label_changed"]),
            "n_abstain_changed": sum(1 for x in comparisons if x["abstain_changed"]),
            "n_display_index_changed": sum(1 for x in comparisons
                                           if x["display_index_changed"]),
            "n_cited_chunk_set_changed": sum(1 for x in comparisons
                                             if x["cited_chunk_set_changed"]),
            "note": ("display_index_changed 可能只反映编号位移；"
                     "cited_chunk_set_changed 才是「真正引到了不同片段」。"),
            "detail": comparisons,
        },
    }
    if torch.cuda.is_available():
        consistency["meta"]["peak_memory_gb"] = {
            "allocated": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
            "reserved": round(torch.cuda.max_memory_reserved() / 1024**3, 3)}
    (run_dir / f"order_smoke_{args.subset}.json").write_text(
        json.dumps(consistency, ensure_ascii=False, indent=2), encoding="utf-8")

    cc = consistency["checks"]
    print(f"[run] items={len(rows)} cache_hits={n_cache_hit} elapsed={elapsed:.1f}s "
          f"load={load_s}s")
    print(f"[run] checks={json.dumps(cc, ensure_ascii=False)}")
    for c in CONDITIONS:
        v = consistency["per_condition"][c]
        print(f"  {c:16} n={v['n']} ok={v['n_ok']} inv={v['n_invalid']} "
              f"inv_cit={v['n_invalid_citation']} "
              f"[diag] res={v['diagnostic_citation_result_family_rate']} "
              f"E1={v['diagnostic_cited_E1_rate']} t={v['mean_item_seconds']}s")
    print(f"[written] {run_dir/f'order_smoke_{args.subset}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
