# BioEvidence v4

Transformers + lm-evaluation-harness 的 Task B 生成接入与证据顺序开发对照。当前完成范围以 V4_STATUS.md 和真实运行报告为准。

历史目录只读。数据是反复使用的 internal_70_30/dev151，非新留出集。四条件只改变预算后固定片段的顺序及显示编号，不分离纯位置效应。基座0.6B、4B Instruct为主比较；冻结E7只用于迁移回归。模型差异同时包含规模及模型版本/指令训练差异，不归因于单一规模或微调效果。

在项目根目录运行 PowerShell：

```powershell
$PY = 'C:\1_yanjiusheng\BioEvidence\BioEvidence-v4\.venv\Scripts\python.exe'
& $PY -X utf8 -B BioEvidence-v4\environment.py
& $PY -X utf8 -B BioEvidence-v4\prepare.py --export
& $PY -X utf8 -B BioEvidence-v4\test_adapter.py
& $PY -X utf8 -B BioEvidence-v4\framework_smoke.py
& $PY -X utf8 -B BioEvidence-v4\offline.py
& $PY -X utf8 -B BioEvidence-v4\generate.py --model e7_06b --n 10 --regression
& $PY -X utf8 -B BioEvidence-v4\generate.py --model base_06b --n 10
& $PY -X utf8 -B BioEvidence-v4\generate.py --model instruct_4b --n 10
& $PY -X utf8 -B BioEvidence-v4\generate.py --model base_06b --n 151
& $PY -X utf8 -B BioEvidence-v4\generate.py --model instruct_4b --n 151
& $PY -X utf8 -B BioEvidence-v4\analyze.py --model base_06b
& $PY -X utf8 -B BioEvidence-v4\analyze.py --model instruct_4b
& $PY -X utf8 -B BioEvidence-v4\prepare.py --verify
& $PY -X utf8 -B BioEvidence-v4\report.py
& $PY -X utf8 -B BioEvidence-v4\finalize.py
```

首次清单已有 source_inventory.json，禁止覆盖重建。prepare --export只重新导出v4文件，不改历史文件。generate强制真实评分一致性报告通过；输入token和system全文断言防止静默截断/遗漏。输出预算耗尽记录原始输出和历史解析状态，计为生成失败；不补字段、不修引用。

每题每条件有独立JSON缓存，键区分权重完整hash、模型配置、模板、解码、输入、条件、代码和依赖。完成的生成含预算耗尽记录可复用，系统异常保留并可续跑；每次运行不无限重试。smoke10和dev151分别保存汇总。正式扩跑1208次唯一请求；先跑80次小样本后，正常缓存命中时剩1128次。

独立环境安装方式：venv使用本机CPython基础运行时，system-site-packages关闭。torch来自旧环境的只读 RECORD 校验快照，安装后的包位于v4，未共享旧环境包；来源、哈希和安装报告见 cuda_snapshot.json、install-snapshot-report.json。其它核心包使用官方PyPI固定版本。requirements-lock.txt由真实pip freeze生成；requirements-hashed.txt从实际安装报告生成。恢复时用wheelhouse和官方源：

```powershell
$env:PIP_CONFIG_FILE='NUL'
$env:PIP_CACHE_DIR='C:\1_yanjiusheng\BioEvidence\BioEvidence-v4\cache\pip'
& $PY -X utf8 -B -m pip install --find-links BioEvidence-v4\wheelhouse --require-hashes -r BioEvidence-v4\requirements-hashed.txt --index-url https://pypi.org/simple
```

4B 下载断点保留在v4/models中；fetch_model.py只使用固定commit的原始safetensors，校验上游LFS SHA256，拒绝不遵守Range的续传响应。未完成权重不能用于生成。可运行命令：

```powershell
& $PY -X utf8 -B BioEvidence-v4\fetch_model.py
```

官方大流/高并发出现提前EOF或TLS失败后，有界分段断点另存ranges中；实测公共镜像4MiB片段与官方已核验原文件一致。可续传同一固定commit并最终核验官方LFS整文件SHA，不升级依赖、不改变权重格式：

```powershell
& $PY -X utf8 -B BioEvidence-v4\fetch_ranges.py --workers 4 --request-mib 4 --endpoint https://hf-mirror.com
& $PY -X utf8 -B BioEvidence-v4\run_remaining.py
```

本轮0.6B全量已完成后，4B在176条缓存处因会话中断结束。专用续跑入口保留0.6B原汇总和4B前段日志，登记剩余请求成本后复用已完成缓存：

```powershell
& $PY -X utf8 -B BioEvidence-v4\continue_full.py
```

完成标记存在时该入口直接退出，不新增模型调用。逐条真实输出的额外完整性核验可运行 `verify_outputs.py --scope dev151`，模型调用为0。

镜像仅改变传输端点；探测、失败记录及混合断点来源单独保存。无认证token传给镜像。AI辅助审核的匿名输入、锁定意见、定位核验和解封汇总位于ai_assisted；不作为人工真值。gpu_monitor.py另记录整卡显存采样，包含桌面等其他进程，与逐条CUDA allocator峰值分开解释。

机械评分直接调用冻结 v2_stageb_dev_analysis.metrics。v1兼容汇总调用原compute_metrics；两者不擅自统一分母。契约完整性另列诊断，不改变历史解析定义。“引用合法”“引用落结果族”“文献身份代理Answerable”都不等同语义支持或人工充分性。human_dev26_reference记录核验的26条历史人工参考，覆盖及充分/不足分母另报；unknown/N/A不记通过。McNemar仅用于同题正确/错误配对，macro-F1不作该检验。

离线回放参考来自独立历史冻结预测和对应汇总，模型调用为0；它与7项风险测试、官方框架冒烟分别记录。本轮实际使用官方arc_easy 5条，没有以合成替代任务完成真实一致性。已交付1208条两模型开发生成与最终报告；完成状态见V4_STATUS.md，交付文件hash见reports/delivery_manifest.json。
