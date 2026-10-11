# BioEvidence

**生物医学文献证据问答的可审计评测与领域适配项目。** 在 RTX 3070 8 GB 上，完成检索与固定证据装配、四字段生成、历史评分器迁移、跨模型证据顺序对照，以及微调前后的行为分析。

项目分别评估标签分类、输出契约、弃答和引用行为，并记录证据支持与参考标签的边界。最新 V5 结果显示：**领域微调可以改善格式和部分分类表现，同时退化其他类别召回与证据不足时的弃答行为。**

[最新主要发现](BioEvidence-v5/reports/V5_FINDINGS.md) · [V5 完整报告](BioEvidence-v5/reports/V5_REPORT.md) · [V4 框架接入报告](BioEvidence-v4/reports/V4_REPORT.md) · [发布范围与复算](publication/README.md) · [历史项目总览](docs/PROJECT_OVERVIEW.md)

## 快速核验

从仓库根目录运行，只需 Python 3.10+，无需 GPU 或第三方依赖：

```powershell
python -X utf8 -B publication/verify_release.py
```

该命令校验 256 个发布源文件的 SHA256 和无损压缩，调用原历史解析器与分类评分入口，复算 V4 两模型和 V5 四配置的全部条件，并核对独立冻结的 E7 开发参考。V4/V5 合计检查 3,624 条存储记录，其中包含跨版本复用记录，不能当作 3,624 次独立新生成。

这一步复算已经发布的结果。真实 harness 接入、离线评分一致性、模型生成与训练的原始记录另存于各版本目录；重新生成所需的模型、环境和历史归档见下文。

## 系统与评测对象

```mermaid
flowchart LR
    Q[问题与开发数据] --> E[检索或固定证据装配]
    E --> O[固定内容与预算后的顺序干预]
    O --> M[模型与原生聊天模板]
    M --> C[Label / Reason / Citations / Answerable]
    C --> P[原历史解析器与评分器]
    P --> R[逐条结果 / 分母 / 配对变化 / 成本]
    C --> A[单独保存的 AI 辅助语义复核]
```

Task B 要求四字段输出：

```text
Label: yes | no | maybe
Reason: one sentence grounded in the evidence
Citations: E1, E3 | None
Answerable: yes | no
```

`Label` 表示结论方向，`Answerable` 表示所给证据是否足够；`maybe` 不等于证据不足。引用编号通过稳定 chunk ID 回溯到实际片段。分类正确、引用合法、理由受证据支持是不同指标。

V1 主线使用 PubMedQA、BM25 与章节配额检索；V4/V5 只读复用开发集和预算后的固定证据。V3 在给定上下文上进行流程评测，尚未完成与检索管线的端到端集成。

## V1–V5 的职责

| 版本 | 已完成工作 | 公开入口 |
|---|---|---|
| V1 | 数据、检索、0.6B QLoRA、Task B 契约与评分；历史 test 一次性评测与冻结 | [历史总览](docs/PROJECT_OVERVIEW.md)、[历史指标口径](docs/EVALUATION_FRAMEWORK.md) |
| V2 | 监督目标与充分性审计、证据顺序对照、小样本成对微调探索；保留负结果 | [历史指标口径](docs/EVALUATION_FRAMEWORK.md)、[失败分类](docs/FAILURE_TAXONOMY.md) |
| V3 | 27B 三值量化模型本地推理、回答流程 A/B 对照、30 条新文献探索性评估 | [模型身份](docs/MODEL_IDENTITY.md)、[历史总览](docs/PROJECT_OVERVIEW.md)、[演示 HTML](demo/index.html) |
| V4 | Transformers HF 后端与 lm-evaluation-harness 自定义生成任务；604 条真实历史输出评分一致性；两模型四顺序共 1,208 次开发生成 | [报告](BioEvidence-v4/reports/V4_REPORT.md)、[一致性报告](BioEvidence-v4/reports/SCORING_PARITY.md)、[原运行命令](BioEvidence-v4/README.md) |
| V5 | 与冻结 E7 对齐的 4B QLoRA；两未领域适配配置＋两 adapter 配置；四组四顺序开发对照 | [主要发现](BioEvidence-v5/reports/V5_FINDINGS.md)、[完整报告](BioEvidence-v5/reports/V5_REPORT.md)、[训练对齐](BioEvidence-v5/reports/E7_training_alignment.json)、[原运行命令](BioEvidence-v5/README.md) |

V1–V3 的完整运行归档不包含在此公开仓库中，历史展示文档保留其原口径；`historical_dependencies` 是用于 V4/V5 审计和离线复算的最小原样源码及冻结开发参考快照。

## 最新结果：四组微调前后对照

以下为预定 B0 原顺序、相同 dev151 问题与固定证据的 Task B 结果。这里“未领域适配”指未进行 BioEvidence 微调；4B Instruct 本身已经接受指令训练。0.6B 冻结 E7 与 V2 C-1 old-target adapter 是不同对象。

| 模型配置 | Accuracy | Macro-F1 | 严格机械契约违规 /151 | 不足仍作答 /14 | 充分却弃答 /12 |
|---|---:|---:|---:|---:|---:|
| Qwen3-0.6B，未领域适配 | 0.5430 | 0.2346 | 128 | 14 | 0 |
| Qwen3-0.6B，冻结 E7 | 0.4901 | 0.3617 | 0 | 9 | 1 |
| Qwen3-4B-Instruct-2507，未领域适配 | 0.5695 | 0.4675 | 20 | 9 | 0 |
| Qwen3-4B-Instruct-2507，V5 QLoRA | 0.6424 | 0.4492 | 1 | 11 | 0 |

分类分母为全部 151 题，invalid 计错，固定标签集为 yes/no/maybe，逐类参考数量为 83/51/17；公式沿用原历史评分入口。充分性参考只覆盖 26 题，分别为不足 14、充分 12，其余未知；这两个子集不能外推到全部 151 题。

- **0.6B：** E7 的 macro-F1 上升，但 accuracy 下降；不足仍作答减少，充分却弃答增加 1 题。未适配配置几乎全部预测 yes，低标签变化不能解释为可靠推理。
- **4B：** accuracy 上升、契约违规减少，但 macro-F1 下降，maybe 召回从 5/17 降至 0/17；不足仍作答从 9/14 增至 11/14。结果是收益与退化并存。
- **格式与语义分开：** 0.6B 未适配配置在 B0 的 128 条严格机械违规均为引用字段末尾句号，不能全部解释为语义不忠实。可解析也不等于完整契约通过。

分类参考是原问题的方向标签，在检索证据不足时，恰当弃答也可能被分类指标记错。分类、弃答与证据支持需要分别解释。不同起始模型的规模、版本和指令训练历史不同，两个微调前后差值不能隔离纯参数规模效应。

## 证据顺序对照

四条件固定预算后的实际证据片段，只改变排列及对应显示编号：B0 原顺序、B1 结果族优先、B2 逆序、B3 固定种子随机顺序。结果族沿用历史 RESULT/FINDING 定义。

| 配置 | 四条件 Macro-F1 范围 | B1/B2/B3 相对 B0 标签变化（各 /151） |
|---|---:|---|
| 0.6B 未领域适配 | 0.2346–0.2365 | 1 / 1 / 1 |
| 0.6B 冻结 E7 | 0.2876–0.3888 | 78 / 69 / 56 |
| 4B 未领域适配 | 0.4474–0.5009 | 31 / 34 / 30 |
| 4B V5 QLoRA | 0.4135–0.4492 | 24 / 26 / 20 |

这是“顺序＋重新编号”的干预，不能分离纯位置效应。B1 有 2 题、B3 有 21 题实际输入未变，完整报告单独分层；引用变化按实际 chunk 集合计算，不把 E1→E3 自动当作引用内容变化。全部四条件均报告，未挑选最有利条件宣布有效。

V5 共 **2,416 条比较记录**：V4 未适配模型 1,208 条与历史 E7 604 条经逐条核验复用，新 4B adapter 实际新增生成 604 条。冒烟与 B0 扩跑通过缓存计一次，不重复计算请求或成本。

## 实现与实测成本

V4/V5 使用独立环境、Transformers HFLM 后端与薄适配层，自定义任务调用原解析器、评分器和 aggregation。保留完整提示、证据原文及顺序、显示编号映射、raw 输出、解析错误、配置指纹、缓存键与可取得的遥测。

4B 以 NF4 4-bit、double quantization、BF16、batch size 1 运行。V5 训练完全复用 E7 的 582 条历史目标，固定三轮、219 次更新；最长完整训练输入含 TRL EOS 为 942 token，未截断证据或监督正文，未根据 dev151 选择 checkpoint。

| V5 实际成本 | 数值 |
|---|---:|
| 完整训练 | 26.71 分钟，219 次更新 |
| 604 条唯一新增生成 | 累计 48.29 分钟，28,868 token |
| 训练 CUDA 分配峰值 | 3.365 GiB |
| 生成 CUDA 分配峰值 | 2.836 GiB |

耗时不含安装、加载和校验；CUDA allocator 峰值与包含桌面进程的整卡显存采样分别记录。E7 历史实际生成 token、停止信息和逐请求显存缺失，保留 unknown，重 token 化长度不冒充实际生成长度。

## 语义复核与结果边界

[新增 V5 复核](BioEvidence-v5/ai_assisted/AI_REVIEW.md)由两个当前任务内 AI 子agent各自审核四配置的同样两个匿名问题，共 16 条意见。模型、条件、参考标签及先前结论隐藏；42 处原文定位通过后先锁定、再解封配对。它仅用于案例解释，是 **AI 辅助复核**，不是真实专家、独立人工审核或整体语义真值。

V4/V5 使用反复参与开发的 dev151，**不是新留出评测**。V5 为单训练种子、固定最终 checkpoint；没有重新运行历史 test 或 V3 验收。历史保护检查确认 1,590 个受保护文件的 SHA256 与修改时间未变。

无 RESULTS 不自动代表不足，有 RESULTS 不自动代表充分；非显著不自动代表无效、等效或安全。训练集中 149/342 条 Answerable=yes 无结果族只是结构标志，不等于 149 条错误目标。输出理由不是模型内部推理过程的直接证据。

V3 新文献探索性结果另有暂定参考、7 条待裁决记录、AI 辅助评审及不足样本仅 1 条等限制，见[历史总览](docs/PROJECT_OVERVIEW.md)。其数据与证据条件不同，不能与上面的 dev151 排名比较。

## 仓库内容与重新生成

| 路径 | 内容 |
|---|---|
| [BioEvidence-v4](BioEvidence-v4/) | 标准框架接入、自定义 Task B、评分一致性、两模型顺序实验与逐条产物 |
| [BioEvidence-v5](BioEvidence-v5/) | 训练协议与日志、四组配对、失败案例、成本和 AI 辅助复核 |
| [historical_dependencies](historical_dependencies/) | 原历史函数和冻结开发参考的最小快照 |
| [publication](publication/) | 公开文件清单、原始/发布 SHA256、无 GPU 复算入口与发布边界 |
| [docs](docs/) / [demo](demo/) | V1–V3 历史展示材料与静态案例演示 |

公开副本包含代码、配置、依赖锁、逐条结果、报告与审核记录。模型权重、LoRA 权重、虚拟环境、缓存、wheelhouse 与 checkpoint 留在本地；大型 harness 日志无损 gzip，原始哈希保留。含临时签名下载 URL 的安装报告未发布。

原开发入口保留本机模型路径和历史归档依赖，完整重新生成需要准备相应模型/adapter、历史开发归档及独立环境；不能把“全新 clone 后的离线复算”当作“重新训练和生成”。具体命令与范围见 [V4 README](BioEvidence-v4/README.md)、[V5 README](BioEvidence-v5/README.md)和[发布说明](publication/README.md)。
