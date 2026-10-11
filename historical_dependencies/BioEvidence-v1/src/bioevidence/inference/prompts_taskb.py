#!/usr/bin/env python3
"""Task B：结构化证据问答的提示模板与严格解析。

## 为什么另开一个模块，而不改 prompts.py

`prompts.py` 里的 Task A 模板（`tpl_v2_20260920`）已经产出了 E4/E5/E6 的全部结果。
**改动它会让那些结果无法复现**。因此 Task B 用独立模块 + 独立版本号，
Task A 的模板保持冻结。两套模板可以并存、各自可追溯。

## 输出契约

```
Label: yes | no | maybe
Reason: <一句基于证据的话>
Citations: <证据编号，如 E1, E3；证据不足时写 None>
Answerable: yes | no
```

### 四个字段的语义（必须区分清楚，不能混用）

| 字段 | 含义 | 取值 |
|---|---|---|
| `Label` | 证据指向的**结论方向** | `yes` / `no` / `maybe` |
| `Reason` | 支撑该标签的一句话 | 自由文本 |
| `Citations` | 被引用的证据编号（**必须来自所给证据块**） | `E1, E3` 或 `None` |
| `Answerable` | **所给证据本身**是否足以支撑判断 | `yes` / `no` |

**关键纪律**：
* `Answerable: no` 表示「证据不足」。它**不是** `maybe` 的同义词。
  设计上 `Answerable: no` 时 `Label` 取 `maybe`（因为方向无法确定），
  但两者记录的是不同的东西：一个是「证据够不够」，一个是「方向是什么」。
  这个语义重叠是**已知的设计张力**，在此显式记录，不假装不存在。
* `Citations` 只能引用**所给证据块里真实存在的编号**，且 `Answerable: no` 时必须为 `None`。
  引用不存在的内容是最严重的失败模式，解析器会把它标为 `invalid_citation`。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TEMPLATE_VERSION = "tpl_taskb_v1_20260920"

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


@dataclass
class ParsedTaskB:
    status: str                      # ok | invalid | invalid_citation
    label: str | None = None
    reason: str | None = None
    citations: list[int] = field(default_factory=list)   # 引用到的 E 编号（1-based）
    answerable: str | None = None
    parse_note: str = ""
    citation_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status, "label": self.label, "reason": self.reason,
            "citations": self.citations, "answerable": self.answerable,
            "parse_note": self.parse_note, "citation_issues": self.citation_issues,
        }


def build_messages(question: str, evidence_block: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(
            question=question, evidence_block=evidence_block)},
    ]


def parse_output(text: str, n_evidence: int) -> ParsedTaskB:
    """严格解析 Task B 输出。

    `n_evidence` 是本次提示里实际提供的证据条数（即合法的 E 编号上界）。
    引用超出该上界 → `invalid_citation`。这是最需要被抓出来的失败模式：
    模型编造了一个不存在的证据编号。
    """
    if text is None or not text.strip():
        return ParsedTaskB(status="invalid", parse_note="空输出")

    # 四个字段都是**必需**的：缺任何一个都算格式失败（invalid），
    # 而不是「ok + 小提示」——否则「格式遵循率」这个指标就失去意义。
    # 三层判定：
    #   invalid          —— 缺少必需字段或 Label 不可解析（格式失败）
    #   invalid_citation —— 引用了不存在的证据编号（最严重的失败模式）
    #   ok + issues      —— 格式合规但语义自相矛盾（如 Answerable=no 却给了引用）
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
                           parse_note=f"缺少必需字段 {missing}（不做补救性猜测）")

    label = m_label.group(1).lower()
    reason = m_reason.group(1).strip()
    answerable = m_ans.group(1).lower()

    # ---- Citations ----
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

    out_of_range = [c for c in citations if c < 1 or c > n_evidence]
    if out_of_range:
        citation_issues.append(
            f"引用了不存在的证据编号 {out_of_range}（本次仅提供 E1..E{n_evidence}）")
    citations = sorted(c for c in citations if 1 <= c <= n_evidence)

    # ---- 一致性规则 ----
    if answerable == "no" and citations:
        citation_issues.append("Answerable=no 却给出了引用（按契约应为 None）")
    if answerable == "no" and label != "maybe":
        citation_issues.append(f"Answerable=no 但 Label={label}（按契约应为 maybe）")

    status = "invalid_citation" if out_of_range else "ok"
    note = "解析成功" if not citation_issues else "；".join(citation_issues)
    return ParsedTaskB(status=status, label=label, reason=reason,
                       citations=citations, answerable=answerable,
                       parse_note=note, citation_issues=citation_issues)


def template_fingerprint() -> str:
    import hashlib
    payload = f"{TEMPLATE_VERSION}\n{SYSTEM_PROMPT}\n{USER_TEMPLATE}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
