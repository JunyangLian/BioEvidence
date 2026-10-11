# AI 辅助语义案例复核

两批盲审均先锁定意见、核验逐字定位，再解封条件映射。共16条输出、2道开发题、2个当前任务内AI子agent、48处证据定位。精确agent模型标识不可取得，原样记录unknown。不是实际专家审核或独立人工真值。

| 维度 | 0.6B输出对应AI意见（8条） | 4B输出对应AI意见（8条） |
|---|---|---|
| evidence_sufficiency | insufficient=4; sufficient=4 | insufficient=4; sufficient=4 |
| evidence_supports_reason | partial=7; unsupported=1 | supported=6; partial=1; unsupported=1 |
| reason_supports_label | partial=4; supported=1; unsupported=3 | unsupported=4; supported=4 |
| citation_traceability | supported=8 | N_A=1; supported=7 |
| citation_support | partial=7; unsupported=1 | N_A=1; partial=6; supported=1 |
| abstention_appropriateness | N_A=8 | supported=2; N_A=6 |

此表记录原始意见分布，不计算通过率。N_A和unknown不能记作通过；每个问题在四条件下重复，不能当成16道独立问题。
两批对证据充分性的意见在同题上一致，但Reason支持、引用支持等判断针对不同输出，且审核agent与模型配置混杂，不能据此宣布跨模型优劣。
案例10411439：两批均认为所给片段不足以回答目标体位问题；合法引用仍可能只支持相关背景。4B在部分顺序下弃答，而另一些顺序下作答；这是个案行为观察。
案例10593212：两批均认为证据足以支持给定研究的比较方向；显著性或阴性结果仍不自动证明普遍无效、等效或安全。
审核仅依据给定片段和可见输出；引用可回溯性只核对显示编号至匿名片段，外部文献来源核验为unknown。输出Reason不是内部推理过程的直接证据。意见不回写历史人工标签。
原始盲化意见与锁定SHA分别见ratings_blinded.json、batch2/ratings_blinded.json及对应audit_lock.json；解封记录与逐条件评定另存ratings_unsealed.json。
