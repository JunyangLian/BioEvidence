# BioEvidence V5：领域适配开发对照

0.6B使用冻结E7；4B独立环境使用完全相同582条历史目标，固定3轮/219更新，采用最终checkpoint。最长原生训练941 token，相同TRL追加EOS后942，582条真实监督掩码均通过，无证据或监督正文截断。历史训练报告表头Task A标识与实际Task B消息不一致，按实际消息与loss mask核验，封存表头未改。
dev151已反复使用，仅为探索性开发配对对照。未用它选checkpoint、调参或改目标；未运行历史test/V3验收。

| 配置 | 条件 | 正确/151 | accuracy | macro-F1 | 解析失败 | 引用越界 | 严格机械契约违规 | 弃答/151 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base_06b | B0_original | 82 | 0.5430 | 0.2346 | 0 | 0 | 128 | 0 |
| base_06b | B1_result_first | 83 | 0.5497 | 0.2365 | 0 | 0 | 110 | 0 |
| base_06b | B2_reversed | 83 | 0.5497 | 0.2365 | 0 | 0 | 107 | 0 |
| base_06b | B3_shuffled | 83 | 0.5497 | 0.2365 | 0 | 0 | 124 | 0 |
| e7_06b | B0_original | 74 | 0.4901 | 0.3617 | 0 | 0 | 0 | 14 |
| e7_06b | B1_result_first | 52 | 0.3444 | 0.2876 | 0 | 0 | 0 | 12 |
| e7_06b | B2_reversed | 58 | 0.3841 | 0.3435 | 0 | 0 | 0 | 12 |
| e7_06b | B3_shuffled | 69 | 0.4570 | 0.3888 | 0 | 0 | 0 | 17 |
| instruct_4b | B0_original | 86 | 0.5695 | 0.4675 | 0 | 0 | 20 | 20 |
| instruct_4b | B1_result_first | 85 | 0.5629 | 0.4653 | 0 | 0 | 17 | 17 |
| instruct_4b | B2_reversed | 84 | 0.5563 | 0.4474 | 0 | 0 | 21 | 22 |
| instruct_4b | B3_shuffled | 90 | 0.5960 | 0.5009 | 0 | 0 | 20 | 20 |
| tuned_4b | B0_original | 97 | 0.6424 | 0.4492 | 0 | 0 | 1 | 9 |
| tuned_4b | B1_result_first | 90 | 0.5960 | 0.4135 | 0 | 0 | 1 | 8 |
| tuned_4b | B2_reversed | 92 | 0.6093 | 0.4328 | 0 | 0 | 0 | 10 |
| tuned_4b | B3_shuffled | 90 | 0.5960 | 0.4157 | 0 | 0 | 0 | 7 |

| 同一起始模型：微调后减微调前 | 条件 | Δaccuracy | Δmacro-F1 | Δ契约违规数 | Δ不足仍作答/14 | Δ充分却弃答/12 | 正确→错/错→正确 | McNemar探索性p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base_06b_to_e7_06b | B0_original | -0.0529 | +0.1271 | -128 | -5 | +1 | 23/15 | 0.25588 |
| base_06b_to_e7_06b | B1_result_first | -0.2053 | +0.0511 | -110 | -3 | +2 | 57/26 | 0.00088 |
| base_06b_to_e7_06b | B2_reversed | -0.1656 | +0.1070 | -107 | -3 | +2 | 50/25 | 0.00523 |
| base_06b_to_e7_06b | B3_shuffled | -0.0927 | +0.1523 | -124 | -4 | +3 | 37/23 | 0.09246 |
| instruct_4b_to_tuned_4b | B0_original | +0.0729 | -0.0183 | -19 | +2 | +0 | 12/23 | 0.08953 |
| instruct_4b_to_tuned_4b | B1_result_first | +0.0331 | -0.0518 | -16 | +1 | -1 | 15/20 | 0.49956 |
| instruct_4b_to_tuned_4b | B2_reversed | +0.0530 | -0.0146 | -21 | -1 | -2 | 13/21 | 0.22948 |
| instruct_4b_to_tuned_4b | B3_shuffled | +0.0000 | -0.0852 | -20 | +2 | -1 | 15/15 | 1.0 |

B0：base_06b_to_e7_06b 的macro-F1变化 +0.1271、accuracy变化 -0.0529；严格机械契约违规变化 -128。人工不足子集仍作答变化 -5/14，充分子集错误弃答变化 +1/12。各指标分别解释，不将分类变化自动等同证据使用收益。

B0：instruct_4b_to_tuned_4b 的macro-F1变化 -0.0183、accuracy变化 +0.0729；严格机械契约违规变化 -19。人工不足子集仍作答变化 +2/14，充分子集错误弃答变化 +0/12。各指标分别解释，不将分类变化自动等同证据使用收益。

| 配置 | 条件 | 标签 | support | precision | recall | F1 |
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
| e7_06b | B0_original | yes | 83 | 0.6122 | 0.7229 | 0.6630 |
| e7_06b | B0_original | no | 51 | 0.4231 | 0.2157 | 0.2857 |
| e7_06b | B0_original | maybe | 17 | 0.1111 | 0.1765 | 0.1364 |
| e7_06b | B1_result_first | yes | 83 | 0.5098 | 0.3133 | 0.3881 |
| e7_06b | B1_result_first | no | 51 | 0.2963 | 0.4706 | 0.3636 |
| e7_06b | B1_result_first | maybe | 17 | 0.1053 | 0.1176 | 0.1111 |
| e7_06b | B2_reversed | yes | 83 | 0.5690 | 0.3976 | 0.4681 |
| e7_06b | B2_reversed | no | 51 | 0.3226 | 0.3922 | 0.3540 |
| e7_06b | B2_reversed | maybe | 17 | 0.1613 | 0.2941 | 0.2083 |
| e7_06b | B3_shuffled | yes | 83 | 0.6389 | 0.5542 | 0.5935 |
| e7_06b | B3_shuffled | no | 51 | 0.3673 | 0.3529 | 0.3600 |
| e7_06b | B3_shuffled | maybe | 17 | 0.1667 | 0.2941 | 0.2128 |
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
| tuned_4b | B0_original | yes | 83 | 0.6970 | 0.8313 | 0.7582 |
| tuned_4b | B0_original | no | 51 | 0.6364 | 0.5490 | 0.5895 |
| tuned_4b | B0_original | maybe | 17 | 0.0000 | 0.0000 | 0.0000 |
| tuned_4b | B1_result_first | yes | 83 | 0.6566 | 0.7831 | 0.7143 |
| tuned_4b | B1_result_first | no | 51 | 0.5682 | 0.4902 | 0.5263 |
| tuned_4b | B1_result_first | maybe | 17 | 0.0000 | 0.0000 | 0.0000 |
| tuned_4b | B2_reversed | yes | 83 | 0.6667 | 0.7711 | 0.7151 |
| tuned_4b | B2_reversed | no | 51 | 0.6222 | 0.5490 | 0.5833 |
| tuned_4b | B2_reversed | maybe | 17 | 0.0000 | 0.0000 | 0.0000 |
| tuned_4b | B3_shuffled | yes | 83 | 0.6598 | 0.7711 | 0.7111 |
| tuned_4b | B3_shuffled | no | 51 | 0.5652 | 0.5098 | 0.5361 |
| tuned_4b | B3_shuffled | maybe | 17 | 0.0000 | 0.0000 | 0.0000 |

| 配置 | 条件 | 标签分布 | 严格机械违规类型 | 不足仍作答/14 | 充分却弃答/12 | 人工子集解析/生成失败（不足/充分） |
|---|---|---|---|---:|---:|---:|
| base_06b | B0_original | {'yes': 150, 'no': 1} | {'citation_field_not_comma_separated_ids_or_None': 128} | 14/14 | 0/12 | 0/0 |
| base_06b | B1_result_first | {'yes': 151} | {'citation_field_not_comma_separated_ids_or_None': 110} | 14/14 | 0/12 | 0/0 |
| base_06b | B2_reversed | {'yes': 151} | {'citation_field_not_comma_separated_ids_or_None': 107} | 14/14 | 0/12 | 0/0 |
| base_06b | B3_shuffled | {'yes': 151} | {'citation_field_not_comma_separated_ids_or_None': 124} | 14/14 | 0/12 | 0/0 |
| e7_06b | B0_original | {'maybe': 27, 'yes': 98, 'no': 26} | {} | 9/14 | 1/12 | 0/0 |
| e7_06b | B1_result_first | {'maybe': 19, 'yes': 51, 'no': 81} | {} | 11/14 | 2/12 | 0/0 |
| e7_06b | B2_reversed | {'maybe': 31, 'yes': 58, 'no': 62} | {} | 11/14 | 2/12 | 0/0 |
| e7_06b | B3_shuffled | {'maybe': 30, 'yes': 72, 'no': 49} | {} | 10/14 | 3/12 | 0/0 |
| instruct_4b | B0_original | {'no': 26, 'yes': 94, 'maybe': 31} | {'Answerable=no 却给出了引用（按契约应为 None）': 18, 'Answerable=no 但 Label=no（按契约应为 maybe）': 3} | 9/14 | 0/12 | 0/0 |
| instruct_4b | B1_result_first | {'no': 24, 'maybe': 35, 'yes': 92} | {'Answerable=no 却给出了引用（按契约应为 None）': 15, 'Answerable=no 但 Label=no（按契约应为 maybe）': 3} | 10/14 | 1/12 | 0/0 |
| instruct_4b | B2_reversed | {'no': 22, 'maybe': 34, 'yes': 95} | {'Answerable=no 却给出了引用（按契约应为 None）': 19, 'Answerable=no 但 Label=no（按契约应为 maybe）': 3} | 11/14 | 2/12 | 0/0 |
| instruct_4b | B3_shuffled | {'no': 27, 'maybe': 34, 'yes': 90} | {'Answerable=no 但 Label=no（按契约应为 maybe）': 4, 'Answerable=no 却给出了引用（按契约应为 None）': 17} | 9/14 | 1/12 | 0/0 |
| tuned_4b | B0_original | {'maybe': 8, 'no': 44, 'yes': 99} | {'Answerable=no 但 Label=yes（按契约应为 maybe）': 1} | 11/14 | 0/12 | 0/0 |
| tuned_4b | B1_result_first | {'maybe': 8, 'no': 44, 'yes': 99} | {'Answerable=no 但 Label=yes（按契约应为 maybe）': 1} | 11/14 | 0/12 | 0/0 |
| tuned_4b | B2_reversed | {'maybe': 10, 'no': 45, 'yes': 96} | {} | 10/14 | 0/12 | 0/0 |
| tuned_4b | B3_shuffled | {'maybe': 8, 'no': 46, 'yes': 97} | {} | 11/14 | 0/12 | 0/0 |

| 配置 | 对照B0 | 输入分层 | 配对数 | 标签变化 | Answerable变化 | 实际chunk引用集合变化 | raw变化 |
|---|---|---|---:|---:|---:|---:|---:|
| base_06b | B1_result_first | input_changed | 149 | 1/149 | 0/149 | 33/149 | 147/149 |
| base_06b | B1_result_first | input_unchanged | 2 | 0/2 | 0/2 | 0/2 | 0/2 |
| base_06b | B2_reversed | input_changed | 151 | 1/151 | 0/151 | 23/151 | 149/151 |
| base_06b | B2_reversed | input_unchanged | 0 | N/A(0/0) | N/A(0/0) | N/A(0/0) | N/A(0/0) |
| base_06b | B3_shuffled | input_changed | 130 | 1/130 | 0/130 | 20/130 | 129/130 |
| base_06b | B3_shuffled | input_unchanged | 21 | 0/21 | 0/21 | 0/21 | 0/21 |
| e7_06b | B1_result_first | input_changed | 149 | 78/149 | 10/149 | 22/149 | 141/149 |
| e7_06b | B1_result_first | input_unchanged | 2 | 0/2 | 0/2 | 0/2 | 0/2 |
| e7_06b | B2_reversed | input_changed | 151 | 69/151 | 16/151 | 41/151 | 127/151 |
| e7_06b | B2_reversed | input_unchanged | 0 | N/A(0/0) | N/A(0/0) | N/A(0/0) | N/A(0/0) |
| e7_06b | B3_shuffled | input_changed | 130 | 56/130 | 13/130 | 30/130 | 113/130 |
| e7_06b | B3_shuffled | input_unchanged | 21 | 0/21 | 0/21 | 0/21 | 0/21 |
| instruct_4b | B1_result_first | input_changed | 149 | 31/149 | 7/149 | 64/149 | 149/149 |
| instruct_4b | B1_result_first | input_unchanged | 2 | 0/2 | 0/2 | 0/2 | 0/2 |
| instruct_4b | B2_reversed | input_changed | 151 | 34/151 | 12/151 | 66/151 | 149/151 |
| instruct_4b | B2_reversed | input_unchanged | 0 | N/A(0/0) | N/A(0/0) | N/A(0/0) | N/A(0/0) |
| instruct_4b | B3_shuffled | input_changed | 130 | 30/130 | 8/130 | 41/130 | 128/130 |
| instruct_4b | B3_shuffled | input_unchanged | 21 | 0/21 | 0/21 | 0/21 | 0/21 |
| tuned_4b | B1_result_first | input_changed | 149 | 24/149 | 1/149 | 41/149 | 141/149 |
| tuned_4b | B1_result_first | input_unchanged | 2 | 0/2 | 0/2 | 0/2 | 0/2 |
| tuned_4b | B2_reversed | input_changed | 151 | 26/151 | 5/151 | 50/151 | 122/151 |
| tuned_4b | B2_reversed | input_unchanged | 0 | N/A(0/0) | N/A(0/0) | N/A(0/0) | N/A(0/0) |
| tuned_4b | B3_shuffled | input_changed | 130 | 20/130 | 4/130 | 32/130 | 107/130 |
| tuned_4b | B3_shuffled | input_unchanged | 21 | 0/21 | 0/21 | 0/21 | 0/21 |

历史目标机械分布：Answerable=yes 342条（yes190/no116/maybe36），Answerable=no 240条（全部maybe）；正例单引用E1/E2/E3分别147/130/65。保留原目标，不将其分布等同语义正确；训练目标标签分布与开发参考分布不同也不能自行修正。
分类沿用冻结v2入口：全部151条为分母，invalid计错，固定yes/no/maybe，support为83/51/17；v1口径另存，未统一历史分母。严格机械契约诊断与历史解析状态分开；引用末尾句号计为语法偏离，不能全部解释为语义不忠实。maybe与不足分开，弃答率不预设高低为好。人工充分性只覆盖26题（不足14/充分12），其余未知不自动通过，失败保留分母并单列。
分类参考是原问题方向标签，给定检索证据不足时恰当输出maybe/Answerable=no也可能被该分类指标记错。因此分类分数与恰当弃答分别解释，不能为迁移更改原标签或分母。
理由支持、引用支持与标签正确是不同指标。机械引用合法不能证明引用忠实，输出理由不是内部推理证据。无RESULTS不自动不足；训练342条Answerable=yes中149条无结果族是结构诊断，不等于149条错误目标。
两位AI辅助审核者各自覆盖四组同样2题B0，8个案例/16条意见，42处原文证据定位校验后先锁定再解封模型映射。仅作案例解释，不是真实专家或独立人工真值，不外推模型语义收益。复核中理由关键主张支持改善仍可能伴随理由与标签不一致。完整分歧、保留意见及实际模型标识unknown/unavailable见ai_assisted/AI_REVIEW.md。

| 成本 | 实际值 |
|---|---:|
| comparison_rows | 2416 |
| historical_reuse_rows | 1812 |
| new_unique_generation_requests | 604 |
| new_generation_tokens | 28868 |
| new_generation_seconds | 2897.1426447999747 |
| training_seconds | 1602.727003600001 |
| training_updates | 219 |
| training_peak_allocated_gib | 3.364805221557617 |
| training_peak_reserved_gib | 3.5234375 |
| historical_missing_actual_token_count_rows | 604 |
| new_generation_peak_allocated_gib | 2.8364925384521484 |
| new_generation_peak_reserved_gib | 3.037109375 |
| boundary | Historical per-item timings are provenance only, not newly incurred cost; E7 actual tokens/stop/per-item GPU unknown. Smoke counted once through cache. Installation/download/load excluded. |

复用V4 raw1208条与V2冻结E7 604条；输入、权重、提示、解析及冻结分数逐条核验。E7 B0 raw与P7 151条完全一致，V4另有10条新旧HF/harness迁移回归。E7实际生成token、停止及逐请求显存为unknown；输出重token化长度单列，不冒充实际生成长度。历史后端不同，不能声称604条全部已新生成验证。
两起始模型规模、版本、指令训练历史不同，Δ描述各自领域适配变化，两个Δ不能隔离纯规模效应。顺序含重新编号，不能隔离纯位置效应。全部预注册条件报告，按输入/实现/资源门槛扩跑，不按分数筛选。单训练种子，无稳定性声明；McNemar仅正确/错误探索性配对，未多重校正，不用于macro-F1显著性或证明等效。
训练对齐见E7_training_alignment.json：实际共同参数逐项一致；相同LoRA秩和模块类别仍对应E7 5,046,272与4B 16,515,072个可训练参数，原生模板和token长度不同。历史不存中间checkpoint，V5保存仅供恢复。历史P0版本记录不等于完整P6二进制快照，不声称相同计算预算或训练逐位可复现。

逐条完整输入、稳定chunk映射、raw、解析、错误及指纹见runs/<model>/dev151/predictions.jsonl；失败和分层配对见analysis.json/pairs.jsonl/failure_cases.jsonl。依赖来源、源码hash、adapter完整hash和命令见environment.json、requirements-hashed.txt、训练report.json、README.md。历史保护见reports/historical_protection.json。
