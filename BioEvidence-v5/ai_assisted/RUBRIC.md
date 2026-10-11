# V5 AI辅助生物医药证据复核 v1

这是AI辅助的专家视角模拟，不是真实专家或独立人工审核。只读blind_cases.json和本rubric；禁止读取private_mapping.json、selection.json、其它版本及训练/评测/评分文件。禁止猜测或探查模型、条件、旧标签或前一审核结论。仅基于所给问题、实际证据和原始输出，不查外部医学事实或完整论文；必要时unknown/N/A，不凭缺失内容补事实。

逐条独立评：

- evidence_sufficiency：sufficient/insufficient/unknown。能否回答问题的方向（yes/no/maybe）；条件或未定的方向maybe不等于证据不足。无RESULTS不自动不足，有RESULTS不自动充分。
- reason_key_claim_support：supported/partial/unsupported/unknown，核验理由的关键主张是否由给定片段支持。
- reason_label_alignment：supported/partial/unsupported/unknown，理由是否支持输出方向；不能将相关或描述性事实自动当因果/安全/诊断结论。
- citation_traceability：traceable/not_traceable/unknown/N_A，显示编号是否映射到实际片段；此项仅机械可回溯，不等于语义支持。
- citation_semantic_support：supported/partial/unsupported/unknown/N_A。无引用为N_A并说明；引用存在不等于支持。
- abstention_appropriateness：appropriate/inappropriate/unknown。检查实际Answerable行为；没有弃答也应判断作答是否恰当。不要将弃答率越低或越高当更好。

非显著不自动等于无效、等效或安全；maybe与不足分开。Reason是输出理由，不是内部推理过程证据。充分性关于固定提供证据，不是整篇论文或文献是否真实。

每项给简短中文理由，并为实质结论给evidence_locations：[{"display_id":"E1","chunk_id":"...","quote":"证据原文短引文","supports":"对应判断"}]。需要unknown/N_A时明确缺失或不适用原因，保留意见不得自动通过。

输出JSON：{"audit_kind":"ai_assisted","prompt_version":"v5_ai_biomedical_v1","agent_task":"实际当前任务名","actual_model_identifier":"unknown/unavailable（除非实际取得，不能推测）","timestamp_utc":"实际时间","records":[8条] }。每条含case_id、以上6个枚举项、rationale对象（6项对应理由）、evidence_locations列表、reservations列表。所有8条都要评，不知道的明说。审核锁定后才由主任务解封条件。
