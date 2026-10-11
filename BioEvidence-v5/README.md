# BioEvidence V5

独立的两个未领域适配配置与两个adapter配置对照。V1–V4只读；仅反复开发dev151，不能称新留出。训练目标复用E7的582条历史JSON消息；4B原生非thinking模板，固定3轮最终checkpoint，未根据dev选优。冻结E7与v2 C1 old-target不同。

## 真实命令

目录 C:\1_yanjiusheng\BioEvidence，PowerShell：

~~~powershell
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\offline.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\test_adapter.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\reuse.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\train.py smoke
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\train.py full
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\continue.py
~~~

continue.py依次完成10条B0冒烟、四组B0报告、四顺序全矩阵、真实输入/解析/harness聚合核验、历史保护及交付hash。依据正确性/预算，不依据分数。训练支持最近操作恢复checkpoint，仍选固定最终三轮；已完成无需重新训练，重新训练只用于复现。

单独生成与续跑：

~~~powershell
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\generate.py --model tuned_4b --n 10 --b0-only
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\generate.py --model tuned_4b --n 151 --b0-only
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\generate.py --model tuned_4b --n 151
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\integrity.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\ai_join.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\alignment.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\report.py
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\sources.py --verify
.\BioEvidence-v5\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\finalize.py
~~~

缓存区分模型/adapter完整hash、代码、模板、条件、完整提示、解码和依赖。完成请求复用，失败保留并可恢复；不修复raw或截断证据。新4B共604条，B0与冒烟只计一次。

ai_join.py核验已经完成的盲评文件及锁定hash，再解封配对；不会重新调用审核者。审核文件作为单独AI辅助产物保存，不参与历史评分公式。

## 环境与来源

V5/.venv为独立环境，系统sites关闭。安装复用V4只读CUDA wheel及官方PyPI，baseline全部88版本以require-hashes锁定，TRL1.13.0使用完整baseline约束，未升级既有环境。没有vLLM/LangChain。安装报告含URL和SHA256；requirements-hashed.txt、requirements-lock.txt及environment.json记录独立依赖和实际源码hash。

仅重建尚未创建的独立环境：

~~~powershell
.\BioEvidence-v4\.venv\Scripts\python.exe -X utf8 -B BioEvidence-v5\bootstrap.py
.\BioEvidence-v5\.venv\Scripts\python.exe -B -m pip check
~~~

只读模型：V1的Qwen3-0.6B/冻结E7，V4的Qwen3-4B-Instruct-2507。4B固定revision cdbee75f17c01a7cc42f958dc650907174af0554，完整hash在V4 download_manifest及V5 source_inventory；新adapter完整hash在runs/training/full/report.json。未重复下载权重。

## 产物与边界

- config/protocol.json：训练前锁定数据/目标/轮数/预算。
- reports/training_data_audit.json：582条、349训练题、无dev交集、长度/TaskB消息。
- reports/E7_training_alignment.json：历史实际训练配置与新训练逐项对齐，以及原生模板、可训练参数量、历史后端和保存策略差异；历史P0版本记录不冒充P6完整二进制快照。
- runs/training/smoke和full：582条实际逐token loss mask、有限loss/梯度/显存/optimizer日志、adapter更新与hash。相同TRL末尾追加EOS显式核验，未删正文。
- reports/scoring_parity.json：604条真实历史raw经过实际harness的逐条/计数/分母一致性，另验v1；7项合成风险测试只是补充。
- reports/reuse_integrity.json：V4 raw1208+V2冻结E7 604，共1812条核验复用。
- runs/<model>/dev151/predictions.jsonl：完整输入/证据/chunk编号/raw/错误/指纹/遥测；analysis/pairs/failure_cases另存。
- reports/V5_REPORT.md及development_comparison.json：四组四顺序机械结果、各起始模型自己的前后Δ、失败与成本；B0阶段另存_B0。
- reports/V5_FINDINGS.md：主要发现、预定B0、全部顺序敏感性及实际成本的简版。
- reports/historical_protection.json：1590条封存源/产物/原始权重SHA256及mtime，明确排除V4临时cache/tmp/venv和冗余下载片段。
- ai_assisted/AI_REVIEW.md：两位AI子agent各自覆盖四组同样2题B0，8案例/16条意见；42处原文定位核验后先锁定再解封。保存分歧、保留意见及实际模型标识unknown/unavailable，仅作AI辅助案例解释。

E7复用历史direct Transformers输出，V4另有10条迁移回归，不能声称604条全被新生成验证。实际生成token/停止/逐请求显存未记录，保留unknown；重token化长度另存，不冒充实际生成长度。旧耗时不计本轮新增成本。

新增AI辅助复核仅2题，不是真实专家、独立人工审核或整体语义真值，不能外推模型收益；机械引用合法不能证明引用忠实。人工充分性仅26题，分母不足14/充分12，其余未知；无RESULTS不自动不足，有RESULTS不自动充分，maybe不等于不足。149/342训练yes无结果族只是结构标志，未清洗目标。历史报告表头Task A与实际Task B不一致已核验实际消息，封存表头未改。

起始模型版本/指令训练不同，两个Δ不能隔离纯规模效应；顺序+重新编号非纯位置效应。单训练种子；McNemar仅探索性正确/错误配对，不用于macro-F1显著性或等效性。全部预注册条件报告，没有新增成功门槛。
