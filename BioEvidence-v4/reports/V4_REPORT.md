# BioEvidence v4 开发对照结果

本轮为反复使用的 dev151，非新留出评测。固定预算后的证据内容只改变顺序及显示编号；不能分离纯位置效应。

604 条历史原始输出的真实离线 harness 评分回放通过，逐条解析及各条件整数计数、分母、accuracy、macro-F1 均无差异。v1 原 structural 入口及其冻结汇总另行保持。

在本次dev151上，0.6B无adapter配置几乎全部预测yes，no/maybe召回均为0，accuracy接近参考多数类比例；低标签变化不能解释为可靠推理。4B四条件macro-F1均更高，但maybe precision仍只有约0.14–0.16。同条件跨模型正确/错误McNemar的探索性p为0.3916–1.0；不新增成功门槛，不对macro-F1作显著性声明，也不据此证明无差异或等效。
相对B0，4B的B1/B2/B3分别有31/34/30题标签变化、7/12/8题Answerable变化、64/66/41题实际引用集合变化；0.6B每个对照只有1题标签变化，但引用集合和raw仍有变化。B1结果族优先的4B正确数从86降至85，B2为84，B3为90；没有统一顺序收益，不挑最高条件宣布有效。未改变输入的2题B1及21题B3配对，在两模型中均未出现raw变化。
旧解析器均成功且无越界，但契约问题类型明显不同：0.6B的469条严格机械违规全部为引用字段末尾句号；4B的78条主要是弃答仍引用、或弃答时Label不是maybe。弃答多寡本身不判优劣。人工26题子集中，0.6B各条件不足仍作答14/14；4B为9/14、10/14、11/14、9/14，同时充分却弃答为0/12、1/12、2/12、1/12。这些子集分母不能外推到全部151题。

| 模型 | 条件 | 正确/151 | accuracy | macro-F1 | 解析失败 | 引用越界 | 完整契约违规 | 弃答/151 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base_06b | B0_original | 82 | 0.5430 | 0.2346 | 0 | 0 | 128 | 0 |
| base_06b | B1_result_first | 83 | 0.5497 | 0.2365 | 0 | 0 | 110 | 0 |
| base_06b | B2_reversed | 83 | 0.5497 | 0.2365 | 0 | 0 | 107 | 0 |
| base_06b | B3_shuffled | 83 | 0.5497 | 0.2365 | 0 | 0 | 124 | 0 |
| instruct_4b | B0_original | 86 | 0.5695 | 0.4675 | 0 | 0 | 20 | 20 |
| instruct_4b | B1_result_first | 85 | 0.5629 | 0.4653 | 0 | 0 | 17 | 17 |
| instruct_4b | B2_reversed | 84 | 0.5563 | 0.4474 | 0 | 0 | 21 | 22 |
| instruct_4b | B3_shuffled | 90 | 0.5960 | 0.5009 | 0 | 0 | 20 | 20 |

| 模型 | 条件 | 标签 | support | precision | recall | F1 |
|---|---|---|---:|---:|---:|---:|
| base_06b | B0_original | yes | 83 | 0.5467 | 0.9880 | 0.7039 |
| base_06b | B0_original | no | 51 | 0.0000 | 0.0000 | 0.0000 |
| base_06b | B0_original | maybe | 17 | N/A | 0.0000 | 0.0000 |
| base_06b | B1_result_first | yes | 83 | 0.5497 | 1.0000 | 0.7094 |
| base_06b | B1_result_first | no | 51 | N/A | 0.0000 | 0.0000 |
| base_06b | B1_result_first | maybe | 17 | N/A | 0.0000 | 0.0000 |
| base_06b | B2_reversed | yes | 83 | 0.5497 | 1.0000 | 0.7094 |
| base_06b | B2_reversed | no | 51 | N/A | 0.0000 | 0.0000 |
| base_06b | B2_reversed | maybe | 17 | N/A | 0.0000 | 0.0000 |
| base_06b | B3_shuffled | yes | 83 | 0.5497 | 1.0000 | 0.7094 |
| base_06b | B3_shuffled | no | 51 | N/A | 0.0000 | 0.0000 |
| base_06b | B3_shuffled | maybe | 17 | N/A | 0.0000 | 0.0000 |
| instruct_4b | B0_original | yes | 83 | 0.6596 | 0.7470 | 0.7006 |
| instruct_4b | B0_original | no | 51 | 0.7308 | 0.3725 | 0.4935 |
| instruct_4b | B0_original | maybe | 17 | 0.1613 | 0.2941 | 0.2083 |
| instruct_4b | B1_result_first | yes | 83 | 0.6630 | 0.7349 | 0.6971 |
| instruct_4b | B1_result_first | no | 51 | 0.7917 | 0.3725 | 0.5066 |
| instruct_4b | B1_result_first | maybe | 17 | 0.1429 | 0.2941 | 0.1923 |
| instruct_4b | B2_reversed | yes | 83 | 0.6632 | 0.7590 | 0.7079 |
| instruct_4b | B2_reversed | no | 51 | 0.7273 | 0.3137 | 0.4383 |
| instruct_4b | B2_reversed | maybe | 17 | 0.1471 | 0.2941 | 0.1961 |
| instruct_4b | B3_shuffled | yes | 83 | 0.6889 | 0.7470 | 0.7168 |
| instruct_4b | B3_shuffled | no | 51 | 0.8519 | 0.4510 | 0.5898 |
| instruct_4b | B3_shuffled | maybe | 17 | 0.1471 | 0.2941 | 0.1961 |

| 模型 | 条件 | 预测标签分布（含失败时解析字段） | 严格契约问题类型计数 | 仅引用字段末尾句号语法偏离 |
|---|---|---|---|---:|
| base_06b | B0_original | yes=150; no=1 | citation_field_not_comma_separated_ids_or_None=128 | 128/151 |
| base_06b | B1_result_first | yes=151 | citation_field_not_comma_separated_ids_or_None=110 | 110/151 |
| base_06b | B2_reversed | yes=151 | citation_field_not_comma_separated_ids_or_None=107 | 107/151 |
| base_06b | B3_shuffled | yes=151 | citation_field_not_comma_separated_ids_or_None=124 | 124/151 |
| instruct_4b | B0_original | no=26; yes=94; maybe=31 | Answerable=no 却给出了引用（按契约应为 None）=18; Answerable=no 但 Label=no（按契约应为 maybe）=3 | 0/151 |
| instruct_4b | B1_result_first | no=24; maybe=35; yes=92 | Answerable=no 却给出了引用（按契约应为 None）=15; Answerable=no 但 Label=no（按契约应为 maybe）=3 | 0/151 |
| instruct_4b | B2_reversed | no=22; maybe=34; yes=95 | Answerable=no 却给出了引用（按契约应为 None）=19; Answerable=no 但 Label=no（按契约应为 maybe）=3 | 0/151 |
| instruct_4b | B3_shuffled | no=27; maybe=34; yes=90 | Answerable=no 但 Label=no（按契约应为 maybe）=4; Answerable=no 却给出了引用（按契约应为 None）=17 | 0/151 |

分类按原 v2 口径包含全部151条，invalid计错；固定标签 yes/no/maybe，三类均有参考支持。完整契约机械诊断与历史解析状态分别报告：四个非空行、字段顺序、Label/Answerable严格单词、引用字段严格为None或逗号分隔E编号、原解析器的citation_issues及生成失败。引用列表末尾句号也计为严格语法偏离；不能把这些记录都解释成缺字段、引用越界或语义不支持。该机械诊断不核验Reason的生物医药语义支持，不覆盖所有可能的自然语言约束。弃答率仅作行为诊断。逐类表现、人工参考的覆盖/分母、长度、延迟、显存和失败案例见对应 analysis.json。

| 模型 | 对照 B0 | 输入改变/未变 | 标签变化 | Answerable变化 | 实际引用集合变化 |
|---|---|---:|---:|---:|---:|
| base_06b | B1_result_first | 149/2 | 1/151 | 0/151 | 33/151 |
| base_06b | B2_reversed | 151/0 | 1/151 | 0/151 | 23/151 |
| base_06b | B3_shuffled | 130/21 | 1/151 | 0/151 | 20/151 |
| instruct_4b | B1_result_first | 149/2 | 31/151 | 7/151 | 64/151 |
| instruct_4b | B2_reversed | 151/0 | 34/151 | 12/151 | 66/151 |
| instruct_4b | B3_shuffled | 130/21 | 30/151 | 8/151 | 41/151 |

| 模型 | 对照B0 | 输入分层 | 配对数 | 标签变化 | Answerable变化 | 实际引用集合变化 | raw变化 |
|---|---|---|---:|---:|---:|---:|---:|
| base_06b | B1_result_first | input_changed | 149 | 1/149 | 0/149 | 33/149 | 147/149 |
| base_06b | B1_result_first | input_unchanged | 2 | 0/2 | 0/2 | 0/2 | 0/2 |
| base_06b | B2_reversed | input_changed | 151 | 1/151 | 0/151 | 23/151 | 149/151 |
| base_06b | B2_reversed | input_unchanged | 0 | N/A (0/0) | N/A (0/0) | N/A (0/0) | N/A (0/0) |
| base_06b | B3_shuffled | input_changed | 130 | 1/130 | 0/130 | 20/130 | 129/130 |
| base_06b | B3_shuffled | input_unchanged | 21 | 0/21 | 0/21 | 0/21 | 0/21 |
| instruct_4b | B1_result_first | input_changed | 149 | 31/149 | 7/149 | 64/149 | 149/149 |
| instruct_4b | B1_result_first | input_unchanged | 2 | 0/2 | 0/2 | 0/2 | 0/2 |
| instruct_4b | B2_reversed | input_changed | 151 | 34/151 | 12/151 | 66/151 | 149/151 |
| instruct_4b | B2_reversed | input_unchanged | 0 | N/A (0/0) | N/A (0/0) | N/A (0/0) | N/A (0/0) |
| instruct_4b | B3_shuffled | input_changed | 130 | 30/130 | 8/130 | 41/130 | 128/130 |
| instruct_4b | B3_shuffled | input_unchanged | 21 | 0/21 | 0/21 | 0/21 | 0/21 |

| 同条件跨模型配对 | 标签变化/151 | Answerable变化/151 | 实际引用集合变化/151 | 正确→错 b / 错→正确 c | McNemar p（探索性） |
|---|---:|---:|---:|---:|---:|
| B0_original | 56 | 20 | 80 | 20/24 | 0.65159 |
| B1_result_first | 59 | 17 | 115 | 22/24 | 0.883 |
| B2_reversed | 56 | 22 | 110 | 20/21 | 1.0 |
| B3_shuffled | 61 | 20 | 88 | 21/28 | 0.3916 |

| 模型 | 条件 | 人工覆盖/151 | 不足仍作答/14 | 充分却弃答/12 | 人工子集历史解析/生成失败（不足/充分） |
|---|---|---:|---:|---:|---:|
| base_06b | B0_original | 26/151 | 14/14 | 0/12 | 0/0 |
| base_06b | B1_result_first | 26/151 | 14/14 | 0/12 | 0/0 |
| base_06b | B2_reversed | 26/151 | 14/14 | 0/12 | 0/0 |
| base_06b | B3_shuffled | 26/151 | 14/14 | 0/12 | 0/0 |
| instruct_4b | B0_original | 26/151 | 9/14 | 0/12 | 0/0 |
| instruct_4b | B1_result_first | 26/151 | 10/14 | 1/12 | 0/0 |
| instruct_4b | B2_reversed | 26/151 | 11/14 | 2/12 | 0/0 |
| instruct_4b | B3_shuffled | 26/151 | 9/14 | 1/12 | 0/0 |

人工充分性参考只覆盖固定26题，参考充分/不足分别为12/14；每条件保持这两个完整分母。历史解析或生成失败单列，不自动记为恰当作答或弃答；原解析器允许的契约矛盾另见完整契约诊断，仍可出现在此行为表。该子集不代表全部151题，历史文献身份代理也不代替充分性参考。

配对 JSON 同时保存输入变化/未变化分层、原始输出变化、显示编号与稳定chunk引用集合。McNemar仅检验同题正确/错误配对，未用于macro-F1；多项比较均为探索性，未做多重性校正，也未新增成功门槛。

| 模型 | 唯一请求 | 生成token | 生成秒 | 峰值已分配/保留GiB |
|---|---:|---:|---:|---:|
| base_06b | 604 | 38434 | 1501.8 | 0.632/1.090 |
| instruct_4b | 604 | 31975 | 1747.1 | 2.748/2.887 |

实际加载dtype见output_integrity_dev151.json：harness从模型对象读取的dtype为torch.bfloat16。共享配置为NF4 4-bit、双重量化、bfloat16计算、batch_size=1、最大上下文2048、输出160、greedy。harness本地model_revision=main只是加载默认元数据，不能作为权重来源；完整本地hash和4B固定revision记录在各模型config.json及download_manifest.json。

上述成本包含小样本缓存一次，不重复计费；安装、下载、模型加载、官方框架冒烟及E7回归另记。E7不混入主比较。
CUDA allocator峰值为生成请求期间实际读数；另有活动监测窗口内2秒间隔整卡采样 12098 次，观察峰值 4372MiB，包含桌面等其它进程且可能漏掉短暂峰值。中断之间存在采样空窗；原序列见logs/gpu_memory_series.jsonl。

0.6B基座与4B Instruct的差异同时涉及模型规模、版本与指令训练，不能归因于单一规模，也不能据此证明微调效果。引用合法、结果族引用、语义支持及标签正确分别报告。人工充分性参考只覆盖26题（不足14/充分12），其余未知不记通过。
分类参考来自原问题标签，标签正确不证明给定检索证据支持该答案或理由；maybe是原分类标签，不等于证据不足。Answerable行为另按人工充分性子集诊断。

两批当前任务内子agent的16条盲化AI辅助意见、48处定位已锁定后解封，只覆盖同样2题。精确agent模型运行标识无法取得，记录unknown。每模型由不同agent评定，审核者与模型混杂；此便利小子集不用于总体比例、人工真值或模型优劣结论。记录与限制见ai_assisted/AI_REVIEW.md。

可运行命令见 README.md；依赖及源码来源见 environment.json、requirements-lock.txt、requirements-hashed.txt、reports/source_commits.json；历史封存保护见 reports/historical_protection.json。
