#!/usr/bin/env python3
"""v3-P0 适配层：Task B 语义的输入输出契约（独立于 v1/v2，只读复用其契约语义）。

## 为什么单独一层

v1 的 Task B 契约（`BioEvidence-v1/src/bioevidence/inference/prompts_taskb.py`，
`TEMPLATE_VERSION = tpl_taskb_v1_20260920`）**不得改动**（改了就不可复现）。
本模块是 v3 的**独立适配层**，做三件事：

1. **保持任务指令含义一致**：system / user 指令文本**逐字沿用 v1**，
   并记录 `INSTRUCTION_SOURCE` 与 `instruction_fingerprint()`，便于审计「确实没改语义」。
2. **接入新模型自身的聊天模板**：不再手工拼 `<|im_start|>`；
   只产出 `messages`（system/user），由推理框架用 **GGUF 内置的聊天模板**渲染。
3. **输出透明化**：v1 的 `sorted()` 会丢弃模型给出的引用顺序
   （`prompts_taskb.py:166`，v2 核查已记为「前置工程改动」）。
   v3 **保留原始顺序** `citations_raw_order`，同时给出 `citations`（升序，用于对齐 v1 口径）
   与 `citations_model_order`（去重保序）。这是**记录**，不是修复。

## 与 v1 的差异（必须显式记录，不得静默）

| 项 | v1 | v3-P0 |
|---|---|---|
| 引用顺序 | `sorted()` 丢弃 | 保留原始顺序并同时给出升序 |
| 越界引用 | 从列表剔除，status=invalid_citation | **同样剔除**，但把越界值单独记入 `out_of_range_citations`（v1 只放在 note 文本里） |
| 失败判定 | invalid / invalid_citation | 同 v1 三级，**不新增补救** |

## 输出契约（与 v1 相同）

```
Label: yes | no | maybe
Reason: <一句基于证据的话>
Citations: E1, E3 或 None
Answerable: yes | no
```
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

ADAPTER_VERSION = "v3_adapter_p0_20260924"
INSTRUCTION_SOURCE = ("BioEvidence-v1/src/bioevidence/inference/prompts_taskb.py "
                      "TEMPLATE_VERSION=tpl_taskb_v1_20260920")

# ---------------------------------------------------------------------------
# 指令文本：逐字沿用 v1，保证「任务指令含义一致」可审计
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a biomedical evidence assistant that answers only from the provided evidence.\n"
    "Produce exactly four lines.\n"
    "Line 1 - Label: the direction the evidence supports. Use one of the three words "
    "yes, no, maybe. Use maybe when the evidence is conditional or does not settle the direction.\n"
    "Line 2 - Reason: one short sentence grounded in the evidence.\n"
    "Line 3 - Citations: the evidence ids you used, like E1 and E3, separated by commas. "
    "Write None if you used no evidence.\n"
    "Line 4 - Answerable: whether the provided evidence is sufficient to determine a direction. "
    "Write yes or no. "
    "Write no when the provided evidence does not address the question; "
    "in that case set Label to maybe and Citations to None."
)

USER_TEMPLATE = """Question:
{question}

Evidence:
{evidence_block}

Write exactly four lines, in this order, and nothing else.
The first line starts with "Label:" followed by one of the three words yes, no, maybe.
The second line starts with "Reason:" followed by one short sentence grounded in the evidence.
The third line starts with "Citations:" followed by evidence ids such as E1, E2, or the word None.
The fourth line starts with "Answerable:" followed by either yes or no."""

LABELS = ("yes", "no", "maybe")

# 解析正则沿用 v1 的严格口径（允许包裹符号与全角冒号，不做补救性猜测）
_LABEL_RE = re.compile(
    r"^\s*Label\s*[:：]\s*[<\[\"']?\s*(yes|no|maybe)\s*[>\]\"']?\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE)
_REASON_RE = re.compile(r"^\s*Reason\s*[:：]\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_CIT_RE = re.compile(r"^\s*Citations?\s*[:：]\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_ANS_RE = re.compile(
    r"^\s*Answerable\s*[:：]\s*[<\[\"']?\s*(yes|no)\s*[>\]\"']?\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE)
_ALL_CIT_TOKENS = re.compile(r"\bE\s*(\d+)\b", re.IGNORECASE)
_NONE_TOKENS = re.compile(r"^\s*(none|n/?a|no\s+evidence|\[\]|-)\s*$", re.IGNORECASE)
_THINK_BLOCK = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)


@dataclass
class ParsedTaskB:
    """Task B 解析结果（v3 版）。字段比 v1 更细，但**判定规则不变**。"""
    status: str                                    # ok | invalid | invalid_citation
    label: str | None = None
    reason: str | None = None
    citations: list[int] = field(default_factory=list)              # 升序，与 v1 口径一致
    citations_model_order: list[int] = field(default_factory=list)  # 去重保序（v3 新增）
    citations_raw_order: list[int] = field(default_factory=list)    # 含越界的原始顺序（v3 新增）
    out_of_range_citations: list[int] = field(default_factory=list)  # v3 新增：单独成字段
    answerable: str | None = None
    parse_note: str = ""
    citation_issues: list[str] = field(default_factory=list)
    think_block_present: bool = False
    think_chars: int = 0
    missing_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status, "label": self.label, "reason": self.reason,
            "citations": self.citations,
            "citations_model_order": self.citations_model_order,
            "citations_raw_order": self.citations_raw_order,
            "out_of_range_citations": self.out_of_range_citations,
            "answerable": self.answerable, "parse_note": self.parse_note,
            "citation_issues": self.citation_issues,
            "think_block_present": self.think_block_present,
            "think_chars": self.think_chars,
            "missing_fields": self.missing_fields,
        }


def build_messages(question: str, evidence_block: str) -> list[dict]:
    """只产出 messages；聊天模板由推理框架按 GGUF 内置模板渲染。

    **不**在此处拼接任何特殊 token —— 这正是「使用新模型自身模板」的落点。
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(
            question=question, evidence_block=evidence_block)},
    ]


def parse_output(text: str, n_evidence: int) -> ParsedTaskB:
    """严格解析。规则与 v1 `parse_output` 保持一致，只做**记录层面**的增强。

    三层判定（与 v1 相同）：
      invalid          —— 缺少必需字段或 Label 不可解析（格式失败）
      invalid_citation —— 引用了本次未提供的证据编号（最严重失败模式）
      ok + issues      —— 格式合规但语义自相矛盾（如 Answerable=no 却给了引用）

    `n_evidence` = 本次提示里实际提供的证据条数，即合法 E 编号上界。
    """
    if text is None or not text.strip():
        return ParsedTaskB(status="invalid", parse_note="空输出", missing_fields=["ALL"])

    think = _THINK_BLOCK.search(text)
    think_present = bool(think)
    think_chars = len(think.group(1)) if think else 0

    missing = []
    m_label = _LABEL_RE.search(text)
    if not m_label:
        missing.append("Label")
    m_reason = _REASON_RE.search(text)
    if not m_reason:
        missing.append("Reason")
    m_cit = _CIT_RE.search(text)
    if not m_cit:
        missing.append("Citations")
    m_ans = _ANS_RE.search(text)
    if not m_ans:
        missing.append("Answerable")
    if missing:
        return ParsedTaskB(status="invalid",
                           parse_note=f"缺少必需字段 {missing}（不做补救性猜测）",
                           missing_fields=missing,
                           think_block_present=think_present, think_chars=think_chars)

    label = m_label.group(1).lower()
    reason = m_reason.group(1).strip()
    answerable = m_ans.group(1).lower()

    citations: list[int] = []
    citation_issues: list[str] = []
    raw = m_cit.group(1).strip()
    if not _NONE_TOKENS.match(raw):
        seen = set()
        for num in _ALL_CIT_TOKENS.findall(raw):
            i = int(num)
            if i in seen:
                continue
            seen.add(i)
            citations.append(i)
        if not citations:
            citation_issues.append(f"Citations 行无法解析出编号: {raw[:40]!r}")

    raw_order = list(citations)
    out_of_range = [c for c in citations if c < 1 or c > n_evidence]
    if out_of_range:
        citation_issues.append(
            f"引用了不存在的证据编号 {out_of_range}（本次仅提供 E1..E{n_evidence}）")
    in_range = [c for c in citations if 1 <= c <= n_evidence]

    if answerable == "no" and in_range:
        citation_issues.append("Answerable=no 却给出了引用（按契约应为 None）")
    if answerable == "no" and label != "maybe":
        citation_issues.append(f"Answerable=no 但 Label={label}（按契约应为 maybe）")

    status = "invalid_citation" if out_of_range else "ok"
    note = "解析成功" if not citation_issues else "；".join(citation_issues)
    return ParsedTaskB(status=status, label=label, reason=reason,
                       citations=sorted(in_range),
                       citations_model_order=in_range,
                       citations_raw_order=raw_order,
                       out_of_range_citations=out_of_range,
                       answerable=answerable, parse_note=note,
                       citation_issues=citation_issues,
                       think_block_present=think_present, think_chars=think_chars)


def instruction_fingerprint() -> str:
    return fingerprint_for(ADAPTER_VERSION)


def fingerprint_for(payload_version: str) -> str:
    """与 v1 `template_fingerprint()` **同一算法**的指纹。

    v1: sha256(f"{TEMPLATE_VERSION}\\n{SYSTEM_PROMPT}\\n{USER_TEMPLATE}")[:16]
    因此 `fingerprint_for("tpl_taskb_v1_20260920")` 应当等于 v1 自己算出的值；
    若相等，即可证明「指令文本未被改动」。等值性由
    `scripts/v3_verify_instruction_parity.py` 实际比对，不靠人工声明。
    """
    payload = f"{payload_version}\n{SYSTEM_PROMPT}\n{USER_TEMPLATE}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    print("ADAPTER_VERSION                    :", ADAPTER_VERSION)
    print("instruction_source                 :", INSTRUCTION_SOURCE)
    print("v3 instruction_fingerprint         :", instruction_fingerprint())
    print("fingerprint under v1 TEMPLATE_VERSION:", fingerprint_for("tpl_taskb_v1_20260920"))

