# 真实历史输出评分一致性

已通过：604条独立冻结的开发集原始输出、151题四条件；模型调用0。另单独核验v1 P7的151条分类、解析和结构计分。本报告不是新模型生成成绩，也不是合成测试成绩。

A参考来自v2阶段B独立冻结的predictions_order_dev.jsonl及stageb_dev_analysis.json，并使用v1 P7 A2_quota原始预测与对应metrics。B使用实际lm-evaluation-harness evaluator、generate_until回放、Task.process_results及自定义aggregation。没有把适配器自己的输出当作参考。

逐条原文未改写，status、label、reason、answerable、citations、parse_note、citation_issues均精确一致。历史无独立error_codes字段，将已有status和citation_issues无损映射后与新增日志字段比较；parse_note同时单独比较。每条件样本数、解析状态、Answerable分布、引用行数/总数、问题数、各类support/TP/FP/FN、分母、accuracy和macro-F1均一致。全部差异清单为空。

计分入口调用原函数而不复制新公式。v2主口径为全部151条，invalid计错；标签集合固定yes/no/maybe，各有83/51/17参考支持。原函数先将P/R舍入四位，再计算F1，适配保持该行为。汇总时不会排除格式失败。

v1通用compute_metrics的失败分母与Task B映射存在差别；Task B将解析失败/非法引用映射为invalid计错。v1结构计分埋在eval_taskb.main中，本轮抽取冻结源码的原AST语句执行，结果与独立冻结citation_structural_checks精确一致。Answerable在该历史评分中依赖检索文献身份代理和解析输出子集，不能解释为语义证据充分性。

v2引用诊断使用有引用的输出行作分母，classification使用全部行。v3另有定义和26条审核子集，本轮只读核验，不迁移或重跑其验收。人工充分性仅用实际片段集合核验通过的dev26（不足14/充分12），不与其它证据子集合并。

7项适配风险测试分别覆盖invalid分母、maybe与不足区分、稳定引用映射/原文不变、越界不隐性修复、unknown不通过、零分母、原解析器允许但标记issues的矛盾输出。它们单独保存，未作为本604条一致性检查的替代。

历史解析器会过滤越界引用并返回invalid_citation，也会保留部分结构矛盾为ok加citation_issues。本轮完整保留原始输出和这些原状态/问题；新增完整契约诊断不覆写历史定义。引用可回溯、引用合法、结果族引用、语义支持、标签正确互不等同。

详细数值与逐条日志：scoring_parity.json、../runs/offline/parsed_rows.jsonl、../runs/offline/harness_results.json。可运行入口：../offline.py。
