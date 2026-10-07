# BioEvidence · Portfolio（展示入口）

> **BioEvidence：生物医学文献证据问答的受控评测项目**——审计监督数据与证据充分性，
> 比较检索、微调和回答流程，并分析引用与弃答的失败模式。

本目录是求职/展示的**唯一入口**；项目根目录的 `README.md` 与 v1/v2/v3 各自的文档保持原样（面向开发与复现）。

---

## 一句话

在 8 GB 消费级 GPU 上，围绕"生物医学文献证据问答"完成**检索→证据装配→结构化回答→严格解析→评分与审核**的受控评测系统：审计了监督数据与证据充分性的真值定义，比较了检索条件、微调策略与两种回答流程，并把引用忠实度与弃答行为的失败模式整理成案例库。

## 解决的问题

模型回答医学问题时，"答对标签"远不够：**引用是否真的支撑理由？证据不足时是否诚实弃答？
监督数据本身是否自洽？** 本项目把这三件事做成可复算、可审计、可对照的评测对象。

## 硬件约束（贯穿项目的真实边界）

单卡 **RTX 3070 8 GB** + 16 GB 内存，无外购算力：v1 用 0.6B 模型 + QLoRA；
v3 的 27B 模型以三值量化（1.75 bit/权重，5.9 GB）本地推理（≈28.5 tok/s）；
**27B 的 LoRA 训练经调查无可行路径**（`investigation/lora_ptq10/REPORT.md`），故 v3 走"冻结模型 + 流程对照"。

## 系统图（实际实现；虚线为未做的集成）

```
PubMedQA 结构式摘要（1000 篇 → 3,358 章节 chunk）
        │
        ▼
┌──────────────────────────────┐
│ 检索：BM25 → section-aware 重排 │   ← v1 冻结（A2：BM25 + Results 配额=1）
│ + Results 配额（m=3）          │
└──────────────┬───────────────┘
               ▼  证据块 [E1] (章节) 原文 …（900 token 预算）
┌──────────────────────────────┐
│ 模型：v1 Qwen3-0.6B+LoRA（冻结）│   ← v3 = 27B 三值量化零样本（thinking 关闭）
│      或 v3 27B 三值量化         │
└──────────────┬───────────────┘
               ▼  四行契约：Label / Reason / Citations / Answerable
┌──────────────────────────────┐
│ 严格解析 → 引用映射（E→chunk→PMID）│   ← 三级判定 ok/invalid/invalid_citation
│ → 评分（分类/M1/M2/契约/成本）    │
└──────────────┬───────────────┘
               ▼
        人工审核 / 盲评 / AI 辅助评审（来源分立登记）
- - - - - - - - - - - - - - - - - - - - - -
（虚线）v3 模型 × 检索管线的端到端集成：**未做**——v3 评测均在给定上下文上进行
```

## 三个版本的职责

| 版本 | 职责 | 关键产物 |
|---|---|---|
| **v1** | 建立系统（数据/检索/微调/解析/评分）并完成**官方 test 500 一次性评测**（23 文件冻结清单） | `docs/V3_P1_AB_REPORT.md` §2.1 引用的冻结指标 |
| **v2** | **审计** v1（代码级核查+人工审核包）、受控对照（顺序 B0–B3）、成对微调探索（C-2/C-1，负结果封存） | `V2_IMPLEMENTATION_VERIFICATION.md`、`P3-v2-c1-paired-20260927/` |
| **v3-P1** | 模型接入（27B 三值量化本地部署）、**回答流程对照**（A vs B）、**新文献探索性评估**（30 条） | `docs/V3_P1_ACCEPTANCE_REPORT.md`、`docs/V3_P1_AB_REPORT.md` |

## 主要结果、对照、负结果与限制

**分口径结果**（完整表与出处见 [`EVALUATION_FRAMEWORK.md`](EVALUATION_FRAMEWORK.md §二，自动生成））：

| 版本/条件 | 任务 | 集合 | accuracy | macro-F1 |
|---|---|---|---:|---:|
| v1 多数类基线 | Task A | test 500 | 0.5520 | 0.2371 |
| v1 原 BM25（A0） | Task A | test 500 | 0.5640 | 0.3726 |
| v1 章节配额（A2） | Task A | test 500 | **0.5980** | 0.3922 |
| v1 原 BM25（A0） | Task B | test 500 | 0.4480 | 0.3626 |
| v1 章节配额（A2） | Task B | test 500 | **0.4640** | 0.3599 |
| v2 C-1 new-target（充分性监督） | Task B | dev 151 | 0.1192（**负结果**：弃答率 94.7%） | 0.0816 |
| v3 27B 流程 A（零样本） | Task B | dev 151 | 0.4040 | 0.4084 |
| v3 27B 流程 B（先定位） | Task B | dev 151 | 0.4040 | 0.4157 |
| v3 27B 流程 A | Task B | **新文献验收集 30（暂定参考）** | **0.8276** | 0.6946 |

**弃答与引用（v3 验收集，暂定参考 + AI 辅助评审）**：M1 0/1 · M2 0/29（唯一不足条目被正确弃答）；
解析 30/30；完整契约 29/30（V16 弃答引用非空，违规单列）；证据支持理由 27 支持 + 2 部分支持（/29）；
引用忠实 28 忠实 + 1 部分忠实（/29，弃答 V16 单列核对）。

**负结果与限制**（详见 [`FAILURE_TAXONOMY.md`](FAILURE_TAXONOMY.md)）：
- 充分性监督的小样本微调不可行（C-1 弃答崩坏）；不能外推"全量标注也无效"。
- 两步定位流程未达预设选择门槛（工具辅助盲评：语义净差 −3/−1）→ 采用成本更低的 A。
- 验收集真值含 **7 条待裁决**（预测后才裁决=程序偏差已登记），分数为**暂定**；
  输出评审为 **AI 辅助**，未经独立人工复核；不足样本仅 1 条。
- 验收集问题为机器生成；新文献证据为全文摘要（无检索），与 dev 检索片段不可比。
- v1 人工审核为负责人单人（无第二审核者）。

## 复现与演示（真实命令）

```powershell
# 模型与权重（已在本机，含 SHA256 校验）
#   Ternary-Bonsai-2-27B-PTQ1_0.gguf  SHA256 53107f53…33ee3
#   来源 modelscope.cn/models/prism-ml/Ternary-Bonsai-2-27B-gguf（Apache-2.0）
#   运行时 PrismML llama.cpp 分支 0.2.0-dev build 10709（9a9394a89）

# 启动推理（v3 冻结配置）
& scripts\v3_serve.ps1 -Context 8192

# 流程 A/B 对照（dev151）与最终验收（新文献 30 条）
& $PY scripts\v3_run_ab.py --cache cache\evidence\v3_dev151_b0_evidence.jsonl `
    --out-dir runs\P1-v3-ab-proto-20260930\dev151 --pass A --pass B1 --pass B2
& $PY scripts\v3_run_ab.py --cache cache\evidence\v3_val30_evidence.jsonl `
    --out-dir runs\P1-v3-acceptance-20261001 --pass A

# 发布回归检查（只读；权重/缓存/材料哈希 + 冻结数字核对，10 项）
& $PY scripts\v3_regression_check.py
```

完整环境、来源与口径见 [`../docs/V3_REPRODUCIBILITY.md`](../docs/V3_REPRODUCIBILITY.md)；
交互式演示（检索证据 / 引用跳转 / 弃答）见 [`demo/v3_demo_cases.html`](../demo/v3_demo_cases.html)。

## 文件地图

| 内容 | 文件 |
|---|---|
| 本入口 | `portfolio/README.md` |
| 统一评测框架 + 版本对照表 | `portfolio/EVALUATION_FRAMEWORK.md`（表由脚本回填） |
| 失败案例分类（13 例） | `portfolio/FAILURE_TAXONOMY.md` + 数据附录 `FAILURE_CASES.auto.md` |
| 求职摘要 | `portfolio/RESUME_BULLETS.md` |
| 表格/案例生成器（可重跑） | `portfolio/generate_portfolio_data.py` |
| 版本对照表 / 引用计数（自动） | `portfolio/version_comparison.auto.md`、`portfolio/citation_stats.auto.md` |
| 交互式演示 | `../demo/v3_demo_cases.html` |

## 下一步（已登记，未执行）

1. **独立人工裁决/复核**：7 条待裁决案例（先隐藏模型输出）+ 30 条输出的支持性/忠实度复核；
   结果以追加版本发布，保留本次分数与差异。
2. **另立"充分 vs 不足"受控证据评测**（约 20 篇 × 2 条件）：只评冻结流程 A、评分先固定，
   检验"移除必要支持信息后能否合理弃答"。

详见 [`../docs/V3_NEXT_STEPS.md`](../docs/V3_NEXT_STEPS.md)。
