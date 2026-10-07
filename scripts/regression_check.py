#!/usr/bin/env python3
"""v3 发布回归检查：**只读**，用现有缓存与冻结产物核对关键完整性，不重跑任何实验。

检查项：
  R1 模型权重 SHA256（Ternary Bonsai 2 27B PTQ1_0）
  R2 证据缓存完整性：dev151 B0（151 条）与 val30（30 条）SHA256 + 条数
  R3 人工材料锁定哈希：验收标注源 + A/B 盲评填写稿
  R4 冻结指标与报告口径一致：验收（24/29、M1 0/1、M2 0/29、解析 30/30、契约 29/30）
  R5 A/B 对照冻结数字：dev151 流程 A/B accuracy、dev26 M1/M2
  R6 v1 冻结清单核验记录仍为 23/23（读 P0 产物，不重算）
  R7 关键文档与脚本入口存在

输出：runs/regression_check_<date>.json + 控制台摘要。任何 FAIL 都会让退出码为 1。
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

V3 = Path(r".")
V1 = Path(r"BioEvidence-v1")
V2 = Path(r"BioEvidence-v2")
RUN_P0 = V3 / "runs" / "P0-v3-feasibility-20260924"
RUN_P1 = V3 / "runs" / "P1-v3-ab-proto-20260930"
RUN_ACC = V3 / "runs" / "P1-v3-acceptance-20261001"

MODEL_SHA = "53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3"
DEV151_SHA = "88947fdfed20d149417f64f23de99e9ea4b984b61eeb6ba0b27deea6e1cbd903"
VAL30_SHA = "6ba255675674cf123ae09c2b0544c0c6f0c0687898e30e82f0e1de6f3145e2f2"
ANN_SHA = "bcc3e9d5d0e8cfc94dff33015f0cd9b0d5df163f0649f7e86b47d57cdd12eafa"
ABREV_SHA = "bef4066f5dfa8c955623da5379b0d1d5680e30a858db22864764a3b63822dd6e"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            b = fh.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(p: Path) -> str:
    return hashlib.sha256(p.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def jsonl_lines(p: Path) -> int:
    return sum(1 for l in p.open(encoding="utf-8") if l.strip() and '"sample_id"' in l)


def main() -> int:
    checks = []

    def add(rid, name, ok, detail=""):
        checks.append({"id": rid, "name": name, "ok": bool(ok), "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {rid} {name} {detail}")

    # R1 模型权重
    gguf = Path(r"<model_root>/models/Ternary-Bonsai-2-27B-PTQ1_0.gguf")
    add("R1", "模型权重 SHA256", sha256_file(gguf) == MODEL_SHA, MODEL_SHA[:16] + "…")

    # R2 证据缓存
    dev = V3 / "cache" / "evidence" / "v3_dev151_b0_evidence.jsonl"
    val = V3 / "cache" / "evidence" / "v3_val30_evidence.jsonl"
    add("R2a", "dev151 B0 证据缓存", sha256_file(dev) == DEV151_SHA and jsonl_lines(dev) == 151,
        f"lines={jsonl_lines(dev)}")
    add("R2b", "val30 证据缓存", sha256_file(val) == VAL30_SHA and jsonl_lines(val) == 30,
        f"lines={jsonl_lines(val)}")

    # R3 人工材料锁定哈希
    ann = RUN_P1 / "validation_annotation_filled_source.md"
    abr = RUN_P1 / "ab_review_filled.md"
    add("R3a", "验收标注源锁定", sha256_text(ann) == ANN_SHA)
    add("R3b", "A/B 盲评锁定", sha256_text(abr) == ABREV_SHA)

    # R4 验收冻结指标
    am = json.loads((RUN_ACC / "acceptance_metrics.json").read_text(encoding="utf-8"))
    cls = am["classification_仅充分"]
    ok4 = (am["M1_无依据作答"]["num"] == 0 and am["M1_无依据作答"]["den"] == 1
           and am["M2_错误弃答"]["num"] == 0 and am["M2_错误弃答"]["den"] == 29
           and cls["n_correct"] == 24 and cls["n"] == 29
           and am["format_and_failures"]["n_invalid"] == 0
           and am["format_and_failures"]["n_truncated"] == 0)
    add("R4", "验收冻结指标与报告口径一致",
        ok4, f"acc={cls['accuracy']} M1={am['M1_无依据作答']['num']}/{am['M1_无依据作答']['den']} "
             f"M2={am['M2_错误弃答']['num']}/{am['M2_错误弃答']['den']}")
    # 契约违规 = 1（V16）
    preds = load = [json.loads(l) for l in (RUN_ACC / "predictions_A.jsonl").open(encoding="utf-8")
                    if l.strip() and '"sample_id"' in l]
    n_viol = sum(1 for r in preds if r["parsed"]["citation_issues"])
    add("R4b", "完整契约通过 29/30", n_viol == 1 and preds[0].get("sample_id") is not None,
        f"violations={n_viol}")

    # R5 A/B 冻结数字
    ab = json.loads((RUN_P1 / "ab_metrics.json").read_text(encoding="utf-8"))
    ok5 = (ab["flow_A"]["dev151"]["accuracy"] == 0.404
           and ab["flow_B"]["dev151"]["accuracy"] == 0.404
           and ab["flow_A"]["dev26"]["M1_无依据作答"]["num"] == 1
           and ab["flow_B"]["dev26"]["M1_无依据作答"]["num"] == 2
           and ab["flow_A"]["dev26"]["M2_错误弃答"]["num"] == 2
           and ab["flow_B"]["dev26"]["M2_错误弃答"]["num"] == 2)
    add("R5", "A/B 对照冻结数字", ok5)

    # R6 v1 冻结清单核验记录
    uc = json.loads((RUN_P0 / "untouched_check.json").read_text(encoding="utf-8"))
    add("R6", "v1 冻结清单核验记录 23/23",
        uc["frozen_manifest"]["all_ok"] and uc["frozen_manifest"]["n_all_match"] == 23)

    # R7 关键入口存在
    entries = [
        V3 / "docs" / "V3_PROJECT_OVERVIEW.md",
        V3 / "docs" / "V3_REPRODUCIBILITY.md",
        V3 / "docs" / "V3_DEMO_CASES.md",
        V3 / "demo" / "v3_demo_cases.html",
        V3 / "docs" / "V3_P1_ACCEPTANCE_REPORT.md",
        V3 / "docs" / "V3_P1_AB_REPORT.md",
        V3 / "docs" / "MODEL_IDENTITY.md",
        V3 / "scripts" / "v3_run_ab.py",
        V3 / "scripts" / "v3_serve.ps1",
    ]
    missing = [str(p) for p in entries if not p.exists()]
    add("R7", "关键入口存在", not missing, f"missing={missing}")

    result = {
        "generated_at_local": datetime.now().isoformat(timespec="seconds"),
        "nature": "发布回归检查（只读；使用现有缓存与冻结产物，不重跑实验）",
        "n_pass": sum(1 for c in checks if c["ok"]),
        "n_total": len(checks),
        "all_ok": all(c["ok"] for c in checks),
        "checks": checks,
    }
    out = V3 / "runs" / f"regression_check_{datetime.now():%Y%m%d}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=> {result['n_pass']}/{result['n_total']} PASS; report: {out}")
    return 0 if result["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
