# V4/V5 发布与复算

V4、V5 是真实开发实验的发布副本。源码、配置、依赖锁、逐条输入/证据/输出、分类统计、失败案例、训练日志和 AI 辅助复核保持原始字节；本机封存目录没有改动。每个发布文件与原文件的 SHA256 对应关系见 [release_manifest.json](release_manifest.json)。

只需要 Python 3.10+、不需要 GPU 或第三方依赖的核验命令（从仓库根目录）：

```powershell
python -X utf8 -B publication/verify_release.py
```

它校验全部发布文件、gzip 解压后的原始哈希，调用原历史 `parse_output` 与分类入口，复算 V4 两模型和 V5 四配置的所有条件，并独立核对冻结 E7 参考。它不重新生成模型、不重跑 harness、不构成新的模型能力评测或语义真值认证。原真实 harness 一致性记录见两版 reports/scoring_parity.json。

## 入口

- [V4 报告](../BioEvidence-v4/reports/V4_REPORT.md)：Transformers/HFLM 接入、真实评分一致性、两个模型共1,208次开发生成及证据顺序对照。
- [V5 主要发现](../BioEvidence-v5/reports/V5_FINDINGS.md)：四组共2,416条比较记录，其中1,812条核验复用、本轮604条新增生成。
- [V5 完整报告](../BioEvidence-v5/reports/V5_REPORT.md)：分类、契约、弃答、实际引用集合、顺序敏感性、成本与失败案例。
- [V5 AI 辅助复核](../BioEvidence-v5/ai_assisted/AI_REVIEW.md)：两个问题、两个当前任务内子agent、16条意见，仅作案例解释，非真实专家或独立人工真值。
- [V4 原运行命令](../BioEvidence-v4/README.md) / [V5 原运行命令](../BioEvidence-v5/README.md)。

## 发布范围与复现边界

公开副本不包含 `.venv`、缓存、临时目录、wheelhouse、基座权重、LoRA 权重或训练 checkpoint。权重来源/revision/完整哈希和最终 adapter 哈希保留在模型配置及训练报告。安装报告可能包含临时签名下载 URL，故不发布；固定版本、依赖哈希和来源核验报告保留。

四个较大的 harness_results.json 以 `.json.gz` 无损发布。解压后与原文件字节一致。需要恢复文件名时，例如：

```powershell
python -c "import gzip,pathlib; p=pathlib.Path('BioEvidence-v5/runs/tuned_4b/dev151/harness_results.json.gz'); p.with_suffix('').write_bytes(gzip.decompress(p.read_bytes()))"
```

原开发命令保留本机路径/本地模型/历史文件依赖，不声称在全新 clone 后即可直接重新训练或生成。`historical_dependencies` 仅包含用于审计与无GPU复算的原样历史函数和冻结开发参考，不是完整V1/V2归档。新机器重新生成还需要按原README准备完整历史开发归档、原模型与adapter、独立环境，并调整本机路径；封存保护脚本的绝对路径与mtime是本机保护记录，不能据其在新机器失败判定原结果有误。

数据来源为历史 PubMedQA 开发/训练装配，见原版数据审计和source_inventory；没有新增留出集，没有发布或重新运行历史test或V3验收数据。V5固定同样582条E7监督、三轮最终checkpoint，没有用dev151选checkpoint。不同起始模型的版本/指令训练历史不同；顺序包含重新编号；单种子、人工充分性仅26题、E7旧遥测缺失等限制均保留。

现有仓库根目录的历史展示材料保持其原有实验口径。V4/V5目录中的交付manifest引用完整本机产物，可能包括本次不上传的权重或安装报告；公开副本的实际覆盖范围以 publication/release_manifest.json 为准。
