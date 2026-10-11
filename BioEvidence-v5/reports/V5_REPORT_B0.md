# BioEvidence V5：领域适配开发对照（B0阶段）

0.6B使用冻结E7；4B独立环境使用完全相同582条历史目标，固定3轮/219更新，采用最终checkpoint。最长原生训练941 token，相同TRL追加EOS后942，582条真实监督掩码均通过，无证据或监督正文截断。历史训练报告表头Task A标识与实际Task B消息不一致，按实际消息与loss mask核验，封存表头未改。
dev151已反复使用，仅为探索性开发配对对照。未用它选checkpoint、调参或改目标；未运行历史test/V3验收。

| 配置 | 条件 | 正确/151 | accuracy | macro-F1 | 解析失败 | 引用越界 | 严格机械契约违规 | 弃答/151 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base_06b | B0_original | 82 | 0.5430 | 0.2346 | 0 | 0 | 128 | 0 |
| e7_06b | B0_original | 74 | 0.4901 | 0.3617 | 0 | 0 | 0 | 14 |
| instruct_4b | B0_original | 86 | 0.5695 | 0.4675 | 0 | 0 | 20 | 20 |
| tuned_4b | B0_original | 97 | 0.6424 | 0.4492 | 0 | 0 | 1 | 9 |

| 同一起始模型：微调后减微调前 | 条件 | Δaccuracy | Δmacro-F1 | Δ契约违规数 | Δ不足仍作答/14 | Δ充分却弃答/12 | 正确→错/错→正确 | McNemar探索性p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base_06b_to_e7_06b | B0_original | -0.0529 | +0.1271 | -128 | -5 | +1 | 23/15 | 0.25588 |
| instruct_4b_to_tuned_4b | B0_original | +0.0729 | -0.0183 | -19 | +2 | +0 | 12/23 | 0.08953 |

B0：base_06b_to_e7_06b 的macro-F1变化 +0.1271、accuracy变化 -0.0529；严格机械契约违规变化 -128。人工不足子集仍作答变化 -5/14，充分子集错误弃答变化 +1/12。各指标分别解释，不将分类变化自动等同证据使用收益。

B0：instruct_4b_to_tuned_4b 的macro-F1变化 -0.0183、accuracy变化 +0.0729；严格机械契约违规变化 -19。人工不足子集仍作答变化 +2/14，充分子集错误弃答变化 +0/12。各指标分别解释，不将分类变化自动等同证据使用收益。

| 配置 | 条件 | 标签 | support | precision | recall | F1 |
|---|---|---|---:|---:|---:|---:|
| base_06b | B0_original | yes | 83 | 0.5467 | 0.9880 | 0.7039 |
| base_06b | B0_original | no | 51 | 0.0000 | 0.0000 | 0.0000 |
| base_06b | B0_original | maybe | 17 | N/A | 0.0000 | 0.0000 |
| e7_06b | B0_original | yes | 83 | 0.6122 | 0.7229 | 0.6630 |
| e7_06b | B0_original | no | 51 | 0.4231 | 0.2157 | 0.2857 |
| e7_06b | B0_original | maybe | 17 | 0.1111 | 0.1765 | 0.1364 |
| instruct_4b | B0_original | yes | 83 | 0.6596 | 0.7470 | 0.7006 |
| instruct_4b | B0_original | no | 51 | 0.7308 | 0.3725 | 0.4935 |
| instruct_4b | B0_original | maybe | 17 | 0.1613 | 0.2941 | 0.2083 |
| tuned_4b | B0_original | yes | 83 | 0.6970 | 0.8313 | 0.7582 |
| tuned_4b | B0_original | no | 51 | 0.6364 | 0.5490 | 0.5895 |
| tuned_4b | B0_original | maybe | 17 | 0.0000 | 0.0000 | 0.0000 |

| 配置 | 条件 | 标签分布 | 严格机械违规类型 | 不足仍作答/14 | 充分却弃答/12 | 人工子集解析/生成失败（不足/充分） |
|---|---|---|---|---:|---:|---:|
| base_06b | B0_original | {'yes': 150, 'no': 1} | {'citation_field_not_comma_separated_ids_or_None': 128} | 14/14 | 0/12 | 0/0 |
| e7_06b | B0_original | {'maybe': 27, 'yes': 98, 'no': 26} | {} | 9/14 | 1/12 | 0/0 |
| instruct_4b | B0_original | {'no': 26, 'yes': 94, 'maybe': 31} | {'Answerable=no 却给出了引用（按契约应为 None）': 18, 'Answerable=no 但 Label=no（按契约应为 maybe）': 3} | 9/14 | 0/12 | 0/0 |
| tuned_4b | B0_original | {'maybe': 8, 'no': 44, 'yes': 99} | {'Answerable=no 但 Label=yes（按契约应为 maybe）': 1} | 11/14 | 0/12 | 0/0 |

历史目标机械分布：Answerable=yes 342条（yes190/no116/maybe36），Answerable=no 240条（全部maybe）；正例单引用E1/E2/E3分别147/130/65。保留原目标，不将其分布等同语义正确；训练目标标签分布与开发参考分布不同也不能自行修正。
分类沿用冻结v2入口：全部151条为分母，invalid计错，固定yes/no/maybe，support为83/51/17；v1口径另存，未统一历史分母。严格机械契约诊断与历史解析状态分开；引用末尾句号计为语法偏离，不能全部解释为语义不忠实。maybe与不足分开，弃答率不预设高低为好。人工充分性只覆盖26题（不足14/充分12），其余未知不自动通过，失败保留分母并单列。
分类参考是原问题方向标签，给定检索证据不足时恰当输出maybe/Answerable=no也可能被该分类指标记错。因此分类分数与恰当弃答分别解释，不能为迁移更改原标签或分母。
理由支持、引用支持与标签正确是不同指标。机械引用合法不能证明引用忠实，输出理由不是内部推理证据。无RESULTS不自动不足；训练342条Answerable=yes中149条无结果族是结构诊断，不等于149条错误目标。
两位AI辅助审核者各自覆盖四组同样2题B0，8个案例/16条意见，42处原文证据定位校验后先锁定再解封模型映射。仅作案例解释，不是真实专家或独立人工真值，不外推模型语义收益。复核中理由关键主张支持改善仍可能伴随理由与标签不一致。完整分歧、保留意见及实际模型标识unknown/unavailable见ai_assisted/AI_REVIEW.md。

| 成本 | 实际值 |
|---|---:|
| comparison_rows | 604 |
| historical_reuse_rows | 453 |
| new_unique_generation_requests | 151 |
| new_generation_tokens | 6970 |
| new_generation_seconds | 696.3000757999907 |
| training_seconds | 1602.727003600001 |
| training_updates | 219 |
| training_peak_allocated_gib | 3.364805221557617 |
| training_peak_reserved_gib | 3.5234375 |
| historical_missing_actual_token_count_rows | 151 |
| new_generation_peak_allocated_gib | 2.833538055419922 |
| new_generation_peak_reserved_gib | 3.037109375 |
| boundary | Historical per-item timings are provenance only, not newly incurred cost; E7 actual tokens/stop/per-item GPU unknown. Smoke counted once through cache. Installation/download/load excluded. |

复用V4 raw1208条与V2冻结E7 604条；输入、权重、提示、解析及冻结分数逐条核验。E7 B0 raw与P7 151条完全一致，V4另有10条新旧HF/harness迁移回归。E7实际生成token、停止及逐请求显存为unknown；输出重token化长度单列，不冒充实际生成长度。历史后端不同，不能声称604条全部已新生成验证。
两起始模型规模、版本、指令训练历史不同，Δ描述各自领域适配变化，两个Δ不能隔离纯规模效应。顺序含重新编号，不能隔离纯位置效应。全部预注册条件报告，按输入/实现/资源门槛扩跑，不按分数筛选。单训练种子，无稳定性声明；McNemar仅正确/错误探索性配对，未多重校正，不用于macro-F1显著性或证明等效。

逐条完整输入、稳定chunk映射、raw、解析、错误及指纹见runs/<model>/dev151/predictions.jsonl；失败和分层配对见analysis.json/pairs.jsonl/failure_cases.jsonl。依赖来源、源码hash、adapter完整hash和命令见environment.json、requirements-hashed.txt、训练report.json、README.md。历史保护见reports/historical_protection.json。
