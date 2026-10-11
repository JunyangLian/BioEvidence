# V5 AI辅助语义案例复核

两位当前任务内AI子agent各自评完四组模型的同样2题B0，共16条意见。选择依据为人工参考充分/不足各一题的字典序第一题，排除V4此前两题；没有按模型输出挑题。模型/条件/旧标签/人工参考/前次审核隐藏，完整原始输出及实际片段保留；风格和重复问题可能削弱盲化。
实际agent模型运行标识均无法取得，记录unknown/unavailable。锁定前逐条校验8案例×2、6项枚举、理由和42处原文短引文及稳定chunk定位。锁定文件及时间见audit_lock.json；之后才按private_mapping配对汇总。

这是AI辅助的专家视角模拟，不是真实专家、独立人工真值或整体模型能力评估。仅2题，不能用百分比外推、宣布语义收益或支持模型优劣。两审核者均覆盖全部四组，减少审核者与模型的完全混杂，但不代表独立人类判断。

| agent | 问题 | 微调前→后 | 证据充分性 | 理由关键主张支持 | 理由与标签一致 | 引用语义支持 | 作答/弃答恰当 |
|---|---|---|---|---|---|---|---|
| /root/v5_bio_review_a | 10605400 | base_06b→e7_06b | sufficient -> sufficient | partial -> supported | unsupported -> unsupported | partial -> partial | appropriate -> appropriate |
| /root/v5_bio_review_a | 10605400 | instruct_4b→tuned_4b | sufficient -> sufficient | partial -> supported | partial -> unsupported | unsupported -> partial | appropriate -> appropriate |
| /root/v5_bio_review_a | 11053064 | base_06b→e7_06b | insufficient -> insufficient | partial -> supported | unsupported -> unsupported | unsupported -> partial | inappropriate -> inappropriate |
| /root/v5_bio_review_a | 11053064 | instruct_4b→tuned_4b | insufficient -> insufficient | unsupported -> supported | supported -> unsupported | unsupported -> partial | inappropriate -> inappropriate |
| /root/v5_bio_review_b | 10605400 | base_06b→e7_06b | sufficient -> sufficient | partial -> supported | unsupported -> unsupported | partial -> partial | appropriate -> appropriate |
| /root/v5_bio_review_b | 10605400 | instruct_4b→tuned_4b | sufficient -> sufficient | partial -> supported | partial -> unsupported | unsupported -> partial | appropriate -> appropriate |
| /root/v5_bio_review_b | 11053064 | base_06b→e7_06b | insufficient -> insufficient | unsupported -> supported | unsupported -> unsupported | unsupported -> partial | inappropriate -> inappropriate |
| /root/v5_bio_review_b | 11053064 | instruct_4b→tuned_4b | insufficient -> insufficient | unsupported -> supported | unsupported -> unsupported | unsupported -> partial | inappropriate -> inappropriate |

Unknown/N_A与保留意见保留，未自动记通过。无RESULTS不自动不足，有RESULTS不自动充分；非显著不等于无效/等效/安全。完整意见、分歧、机械可回溯与语义支持区别见ratings_unsealed.jsonl及summary.json。原人工标签未回写。
