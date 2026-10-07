# 失败案例数据附录（自动生成）

生成时间：2026-10-06T16:18:19；生成脚本：`portfolio/generate_portfolio_data.py`。
所有字段取自冻结产物；引号内文本为逐字引用。分析性叙述见 `FAILURE_TAXONOMY.md`。

## F01 · 格式与契约 / 稳定性
- **样本**：question_id=21214884｜划分：test 500（official）｜条件：v1 E7（0.6B）+ A2 检索，greedy，max_new_tokens=160
- **问题**：（问题见预测文件/数据集）
- **实际输入证据**：（B0/A2 检索 3 片段，见预测文件 evidence_meta）
- **原始输出（节选）**：`Label: no
Reason: Of the 32 studied human milk specimens, no 'high-risk' HPV 16, 18, 31, 33, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 35, 39, 3`
- **参考判断及来源**：—（格式失败无参考标签语义）
- **观察到的失败**：输出在 HPY 类型列举处进入重复循环（'35, 39' 交替）直至 token 用尽，解析失败（invalid）
- **归类依据**：重复循环 + 截断；分母处理按冻结口径 invalid 计失败
- **已有干预 / 仍未验证假说**：v1 后将 max_new_tokens 提至 160 覆盖 100% 目标（本条为 test 冻结产物，保持原样） / greedy 解码下的重复循环属已知小模型风险；未做干预实验
- **产物路径**：`v1 runs/P10-test-final-20260922/predictions_e7_taskb_A2_test.jsonl`

## F02 · 监督目标 / 引用问题
- **样本**：question_id=28127977（人工审核 R021）｜划分：dev 151（internal_70_30）｜条件：v1 E7（0.6B）+ A2 检索
- **问题**：Are serum leptin levels a prognostic factor in advanced lung cancer?
- **实际输入证据**：[E1] (BACKGROUND) The aim of this prognostic factor analysis was to investigate if a patient's self-reported health-related quality of life (HRQOL) provided independent prognostic information for survival in non-small cell lung cancer (NSCLC) patients.
[E2] (MATERIAL AND METHODS) There are 71 previously untreated patients with cytological or histological evidence of primary lung cancer who were admitted to the oncology department between November 2013 and August 2014. Forty-five healthy individuals with age, sex and BMI matching the lung cancer patients, were recruited to take part in the study as a control group. Leptin levels were measured quantitatively by using a microELISA kit.
[E3] (RESULTS) The serum leptin levels at diagnosis were significantly lower in lung cancer patients than those in control subjects (4.75±4.91 ng/ml, 9.67±8.02 ng/ml; p<0.001). We did not find any significant difference in leptin values related to clinicopathological parameters such as ECOG PS, weight loss, histological type, disease stage and TNM classification. Nevertheless, we demonstrated a significant correlation between serum leptin levels and BMI in lung cancer patients (correlation coefficient: …
- **原始输出（节选）**：`Label: no
Reason: The aim of this prognostic factor analysis was to investigate if a patient's self-reported health-related quality of life (HRQOL) provided independent prognostic information for survival in non-small cell lung cancer (NSCLC) patients.
Citations: E1
Answerable: yes`
- **参考判断及来源**：人工审核（负责人，单人）：证据是否支持=是；引用是否真的支撑理由=**是，但引用完全不对题**；备注=E3 明确说 leptin 与 overall survival 无关联，所以 no 对；但模型引用的 E1 是另一篇 HRQOL 文献，Reason 与 leptin 问题无关
- **观察到的失败**：引用的 E1 与问题主题无关（引用完全不对题）；且 gold_answerable=yes 为文献身份代理而非语义判断
- **归类依据**：v2 核查将本条定为 R021：可复现读法为 25/25 或 24/25，v1 勘误的 23/25 不可复现
- **已有干预 / 仍未验证假说**：C-2 曾把 Reason/Citations 目标改为人工逐字依据（忠实度改善但语义支持未变） / 监督目标以『命中正确文献』定义 answerable，导致引用语义不被监督
- **产物路径**：`v1 data/review/review_packet_taskb_dev_FILLED.csv（R021 行）+ v2 docs/V2_IMPLEMENTATION_VERIFICATION.md §0.2`

## F03 · 监督目标问题
- **样本**：question_id=10340286（train 349）｜划分：train 349（internal_70_30）｜条件：v1 Task B 训练样本（BM25 top-3，无 section 配额）
- **问题**：Is there a role for leukocyte and CRP measurements in the diagnosis of acute appendicitis in the elderly?
- **实际输入证据**：章节：PMID10340286-SEC00、PMID10340286-SEC01、PMID10340286-SEC02（**无 RESULTS/FINDINGS 章节**）；target Reason = The diagnosis of acute appendicitis is still difficult and the results are unsatisfactory in three particular patient groups: in children, in fertile-age women and in elderly patients.
- **原始输出（节选）**：`Label: maybe
Reason: The diagnosis of acute appendicitis is still difficult and the results are unsatisfactory in three particular patient groups: in children, in fertile-age women and in elderly patients.
Citations: E1
Answerable: yes`
- **参考判断及来源**：训练目标 gold_answerable=yes（由『命中正确文献』推导）
- **观察到的失败**：证据中没有任何结果段，却被监督为『可回答且 Label=maybe』；该形态占训练 yes 样本 43.57%（149/342）
- **归类依据**：v2 核查定位（M-1）；v2 阶段 D 据此把『无结果段』作为标注试点方向
- **已有干预 / 仍未验证假说**：监督以文献身份代理定义 answerable → 该形态被标为可回答（机制假说，未逐条验证） / 『无结果段 + yes』是否直接导致模型在此类输入上过度自信 → 未逐条验证（C-1 为聚合对照，负结果）
- **产物路径**：`v1 data/processed/pubmedqa/sft_taskb.jsonl`

## F04 · 监督目标问题
- **样本**：question_id=10430303（train 349）｜划分：train 349｜条件：v1 Task B 训练样本
- **问题**：Does laparoscopic cholecystectomy influence peri-sinusoidal cell activity?
- **实际输入证据**：引用 chunk PMID10430303-SEC00；Reason 目标 = 该 chunk **全文**（逐字）
- **原始输出（节选）**：`Label: yes
Reason: To investigate the influence of laparoscopic procedures on perisinusoidal cell function.
Citations: E3
Answerable: yes`
- **参考判断及来源**：训练目标 Reason = 整段 chunk（无 '. ' 可切分 → first_sentence() 退化为整段）
- **观察到的失败**：该形态占训练 yes 样本 36.55%（125/342）[v2 核查复算]；监督模型『抄整段』
- **归类依据**：v2 核查定位；C-2 曾尝试修正 Reason 目标（忠实度改善但语义支持未变）
- **已有干预 / 仍未验证假说**：整段监督是否导致引用冗长 → 未做干预实验 / 整段监督是否导致引用冗长/复制 → C-2 修正后忠实度改善但语义支持未变（部分证据）
- **产物路径**：`v1 data/processed/pubmedqa/sft_taskb.jsonl（目标整段形态，聚合 36.55%）`

## F05 · 检索问题 / 证据不足形态
- **样本**：question_id=10593212｜划分：dev 151（A0 原 BM25）｜条件：v1 E7（0.6B）+ A0 检索（无 section 配额）
- **问题**：（问题见预测文件）
- **实际输入证据**：章节：OBJECTIVE、OBJECTIVE、DESIGN（**无 RESULTS/FINDINGS**）；该形态在 A0 下 60/151=39.7%，A2 配额下 0/151
- **原始输出（节选）**：`Label: no
Reason: To investigate the importance of loss of consciousness (LOC) in predicting neuropsychological test performance in a large sample of patients with head injury.
Citations: E2
Answerable: yes`
- **参考判断及来源**：—（该条用于展示证据形态差异，不作为语义真值）
- **观察到的失败**：裸 BM25 检索经常给不出结果段；A2 的 Results quota=1 把该形态从评估分布中整体移除（M-1）
- **归类依据**：v2 阶段 D 将『无结果段』自然样本纳入标注试点（A0 60 条可用）
- **已有干预 / 仍未验证假说**：配额是否真能提升答案质量 → v1 test Task A/B 数字（A0 vs A2）可见差异，但机制归因需对照 / 配额提升是否转化为语义层面的回答改善 → 未做语义对照（现有差异为端到端分类数字）
- **产物路径**：`v1 runs/P6-taskb-20260920/predictions_e7_taskb.jsonl（A0）+ corpus_chunks.jsonl`

## F06 · 证据不足 / 弃答 / 契约
- **样本**：V16（新文献验收集，暂定参考）｜划分：新文献验收集 30｜条件：v3 27B 流程 A（全文 CONTEXTS，无检索）
- **问题**：Do why menopausal women want to take hormone replacement therapy?（语法不完整）
- **实际输入证据**：（全文 3 章节，见 acceptance_review_package.md）
- **原始输出（节选）**：`<think>

</think>

Label: maybe
Reason: The provided survey results detail reasons for not taking HRT but do not report data on why women who are currently taking it chose to use the therapy.
Citations: E1, E3
Answerable: no`
- **参考判断及来源**：暂定参考：evidence_sufficiency=不足；supported_label=N/A（负责人填写稿；**待裁决项**）
- **观察到的失败**：模型正确弃答（Answerable=no），但违反契约：弃答时 Citations 非空（E1,E3）→ 完整契约通过记 29/30
- **归类依据**：弃答判断与暂定参考一致；契约违规为 P0 已登记的模型行为，未修复
- **已有干预 / 仍未验证假说**：Acceptable 的操作口径缺失 → 该题弃答恰当性曾在 A/B 盲评中记『无法判断』，由负责人裁决定案 / 弃答恰当性判断依赖暂定充分性标注（该条本身是待裁决项之一）
- **产物路径**：`v3 runs/P1-v3-acceptance-20261001/predictions_A.jsonl + validation_annotation_filled.csv`

## F07 · 回答支持性问题
- **样本**：V15（新文献验收集，暂定参考）｜划分：新文献验收集 30｜条件：v3 27B 流程 A（全文 CONTEXTS）
- **问题**：Does sarcopenia in Advanced COPD affect Cardiometabolic Risk Reduction by Short-Term High-intensity Pulmonary Rehabilitation?
- **实际输入证据**：（见 acceptance_review_package.md）
- **原始输出（节选）**：`<think>

</think>

Label: yes
Reason: The study shows that short-term high-intensity pulmonary rehabilitation significantly reduced cardiometabolic risk markers like insulin resistance and fat mass only in nonsarcopenic patients, implying sarcopenia impedes this benefit.
Citations: E1, E6
Answerable: yes`
- **参考判断及来源**：暂定参考：充分 + yes；**AI 辅助评审**：摘录支持=部分支持、引用忠实=部分忠实
- **观察到的失败**：理由称改善『only in nonsarcopenic patients』并推断肌少症阻碍获益——E6 只报告组间对比描述，无组别×时间交互检验，且未量化肌少症组变化
- **归类依据**：AI 辅助评审定位为『超出报告强度』；未做独立人工复核
- **已有干预 / 仍未验证假说**：正确做法需组间差异检验；本条为输出质量案例，非发生率估计 / 『组别对比描述』到『阻碍获益』的因果解读未验证
- **产物路径**：`v3 runs/P1-v3-acceptance-20261001/predictions_A.jsonl + acceptance_review_ai_assisted.json（V15）`

## F08 · 引用忠实度问题
- **样本**：T04（dev26 盲评；**工具辅助盲评**）｜划分：dev 151 → dev26 参考子集｜条件：v3 27B 流程 B（先定位）输出 Y = B
- **问题**：Does transverse apex coincide with coronal apex levels (regional or global) in adolescent idiopathic scoliosis?
- **实际输入证据**：（B0 冻结证据，见盲审包）
- **原始输出（节选）**：`## T04

**问题**：Does transverse apex coincide with coronal apex levels (regional or global) in adolescent idiopathic scoliosis?


### 输出 X

X_cited_supports_reason：支持
X_reason_supports_label：部分支持
X_citation_faithfulness：忠实
X_abstention_appropriate：N/A
X_reservations：理由准确区分最旋转水平与冠状面顶点并指出不稳定重合，支持否定可默认重合；它没有明确呈现支持重合与不重合的混合结果或不确定性，因此仅部分支持 maybe；E3 前半计数有疑点，不影响后半差异的直接描述。 工具与范围记录：Codex 辅助核对本包本条输出；本记录尚未经独立人工复核。
审核者：
审核方式：工具辅助（Codex；范围：独立核对本包每条输出的证据支持、标签推理、引用忠实度及弃答，不查看流程映射。）
审核日期：2026-10-01

### 输出 Y

Y_cited_supports_reason：部分支持
Y_reason_supports_label：部分支持
Y_citation_faithfulness：部分忠实
Y_abstention_appropriate：N/A
Y_reservations：E3 支持横断面与冠状面顶点不稳定重合，但 up to two levels 明确针对整体顶点，理由将其同时推广至区域顶点不够忠实；不稳定重合对 maybe 仅提供条件性依据。 工具与范围记录：Codex 辅助核对本包本条输出；本记录尚未经独立人工复核。
审核者：
审核方式：工具辅助（Codex；范围：独立核对本包每条输出的证据支持、标签推理、引用忠实度及弃答，不查看流程映射。）
审核日期：2026-10-01
`
- **参考判断及来源**：工具辅助盲评：Y_citation_faithfulness=**部分忠实**（X=忠实）
- **观察到的失败**：E3 的 up to two levels 仅针对整体顶点，理由将其同时推广至区域顶点——引用忠实度不足
- **归类依据**：工具辅助盲评按冻结序数映射计入 A/B 对照（csr 净 −3 / rsl 净 −1）
- **已有干预 / 仍未验证假说**：泛化性改写是否构成不忠实 → 盲评已给判断，独立人工复核未做 / 把整体顶点结论推广到区域顶点是有意泛化还是疏忽 → 无法判定
- **产物路径**：`v3 runs/P1-v3-ab-proto-20260930/ab_review_filled.md（T04）+ ab_backend_mapping.json`

## F09 · 弃答校准问题
- **样本**：T01（dev26 盲评；**工具辅助盲评**）｜划分：dev 151 → dev26 参考子集｜条件：v3 27B 流程 A 与 B 均 Answerable=no
- **问题**：Is the international normalised ratio (INR) reliable?
- **实际输入证据**：（B0 冻结证据：E2/E3 为两途径 INR 一致性的直接结果）
- **原始输出（节选）**：`## T01

**问题**：Is the international normalised ratio (INR) reliable?


### 输出 X

X_cited_supports_reason：N/A
X_reason_supports_label：N/A
X_citation_faithfulness：忠实
X_abstention_appropriate：不恰当
X_reservations：E2、E3 支持两种途径的 INR 结果相近，理由对总体可靠性的保留亦未捏造事实，但当前已有可作范围限定判断的直接结果，不必要求所有场景的确定结论才允许作答；N/A 仅因本条选择弃答，不代表理由失实。 工具与范围记录：Codex 辅助核对本包本条输出；本记录尚未经独立人工复核。
审核者：
审核方式：工具辅助（Codex；范围：独立核对本包每条输出的证据支持、标签推理、引用忠实度及弃答，不查看流程映射。）
审核日期：2026-10-01

### 输出 Y

Y_cited_supports_reason：N/A
Y_reason_supports_label：N/A
Y_citation_faithfulness：忠实
Y_abstention_appropriate：不恰当
Y_reservations：理由准确区分研究情境内两途径一致性和普遍可靠性，E2、E3 支持其表述；既然已有范围限定的直接结果，缺少总体普遍结论不足以要求弃答，可给出限定性判断。 工具与范围记录：Codex 辅助核对本包本条输出；本记录尚未经独立人工复核。
审核者：
审核方式：工具辅助（Codex；范围：独立核对本包每条输出的证据支持、标签推理、引用忠实度及弃答，不查看流程映射。）
审核日期：2026-10-01
`
- **参考判断及来源**：工具辅助盲评：X/Y 弃答恰当性均为**不恰当**
- **观察到的失败**：证据已有范围限定的直接结果，模型要求『所有场景的确定结论』才肯作答——过度保守弃答
- **归类依据**：与 M2（错误弃答）口径一致：dev26 上 v3 M2 = 2/12（A、B 各 2）
- **已有干预 / 仍未验证假说**：弃答校准与训练分布的关系 → v2 M-1 假说（未验证）；本条为观察 / 过度保守弃答是否与任务训练分布有关 → M-1 假说（未验证）
- **产物路径**：`v3 runs/P1-v3-ab-proto-20260930/ab_review_filled.md（T01）`

## F10 · 引用相关性问题
- **样本**：T06（dev26 盲评；**工具辅助盲评**）｜划分：dev 151 → dev26 参考子集｜条件：v3 27B 流程 A 与 B
- **问题**：Cancer of the buccal mucosa: are margins and T-stage accurate predictors of local control?
- **实际输入证据**：（B0 冻结证据：E3 为胃癌资料）
- **原始输出（节选）**：`## T06

**问题**：Cancer of the buccal mucosa: are margins and T-stage accurate predictors of local control?


### 输出 X

X_cited_supports_reason：N/A
X_reason_supports_label：N/A
X_citation_faithfulness：忠实
X_abstention_appropriate：恰当
X_reservations：E1 的确描述切缘和不同 T 分期肿瘤的局部复发关系为待评估对象，未给出预测能力；E3 属胃癌资料，不能补足颊黏膜癌局部控制结果，弃答恰当。 工具与范围记录：Codex 辅助核对本包本条输出；本记录尚未经独立人工复核。
审核者：
审核方式：工具辅助（Codex；范围：独立核对本包每条输出的证据支持、标签推理、引用忠实度及弃答，不查看流程映射。）
审核日期：2026-10-01

### 输出 Y

Y_cited_supports_reason：N/A
Y_reason_supports_label：N/A
Y_citation_faithfulness：忠实
Y_abstention_appropriate：恰当
Y_reservations：E1、E2 提供切缘、肿瘤分期与局部复发的研究安排，未报告预测结果；E3 的胃癌特异生存分析与目标疾病及结局不符，弃答恰当。 工具与范围记录：Codex 辅助核对本包本条输出；本记录尚未经独立人工复核。
审核者：
审核方式：工具辅助（Codex；范围：独立核对本包每条输出的证据支持、标签推理、引用忠实度及弃答，不查看流程映射。）
审核日期：2026-10-01
`
- **参考判断及来源**：工具辅助盲评：X/Y 均弃答恰当；盲评注明 **E3 属胃癌资料**，与颊黏膜癌局部控制无关
- **观察到的失败**：检索把主题无关的摘要片段带进证据；模型未把它当作目标疾病的证据（未捏造），但引用列表中出现了它
- **归类依据**：检索层缺陷（BM25 词面匹配）；A2 配额只保证 Results 章节，不保证主题相关
- **已有干预 / 仍未验证假说**：无关引用是否会误导回答 → 本条中模型未受其误导（弃答），属观察 / 无关引用在更长上下文中是否会误导回答 → 未验证
- **产物路径**：`v3 runs/P1-v3-ab-proto-20260930/ab_review_filled.md（T06）`

## F11 · 弃答崩坏（微调负结果）
- **样本**：question_id=10605400（C-1 成对评测）｜划分：dev 151｜条件：v2 C-1 new-target（64 条成对重训，充分性监督）
- **问题**：（INR 可靠性同题族；见 C-1 产物）
- **实际输入证据**：（C-1 评测条件，见 paired_eval_report）
- **原始输出（节选）**：`old：Answerable=yes 且正确；new：Answerable=no（弃答）`
- **参考判断及来源**：人工充分性=充分；old 判定正确 → new 弃答为**破坏**（成对方向）
- **观察到的失败**：充分性监督把『不确定』过度泛化为『不足』→ 全量弃答（94.7%，maybe×144/151，分类 0.1192）
- **归类依据**：v2 C-1 封存为负结果；机制（数据重平衡等）已列混淆因素，未分离
- **已有干预 / 仍未验证假说**：弃答崩坏是否由重平衡单独导致 → 未验证（负责人已指出数据重平衡同属训练干预） / 弃答崩坏由数据重平衡单独导致 → 未验证（负责人指出重平衡同属训练干预）
- **产物路径**：`v2 runs/P3-v2-c1-paired-20260927/paired_eval_report.json`

## F12 · 稳定性问题（基础设施）
- **样本**：P0 attempt1（ctx 16384 + f16 KV）｜划分：—（推理基础设施）｜条件：v3 27B 加载阶段
- **问题**：—
- **实际输入证据**：—
- **原始输出（节选）**：`无输出（进程挂死）`
- **参考判断及来源**：—（非模型行为）
- **观察到的失败**：VRAM 7608/8192 MiB 后进程静默挂死（GPU 100%、单核钉住、健康检查 >4min 无变化）；对照：ctx 8192 通过。已登记为**验收程序偏差之外的独立基础设施发现**
- **归类依据**：16384+f16 KV 在本机桌面占用下不可用 → 厂商文档亦有同样记录
- **已有干预 / 仍未验证假说**：处置正确（保留失败记录、换配置重试）；根因未做受控对照（桌面显存占用为混杂因素） / VRAM 挂死的根因（桌面显存占用为混杂因素）未做受控对照
- **产物路径**：`v3 runs/P0-v3-feasibility-20260924/attempts/attempt1_ctx16384_f16_server.log`

## F13 · 格式与契约（提示设计）
- **样本**：question_id 未知（P2 试跑 3 条，原始输出未保留）｜划分：dev 151（P2 试跑段）｜条件：v1 未微调基座 + oracle 证据（E2），模板 v1（含尖括号占位符）
- **问题**：（试跑问题未随产物保留）
- **实际输入证据**：（E2 真值证据）
- **原始输出（节选）**：`error_log 登记的实际行为：模型输出 `Label: <yes>`（连尖括号一起抄），被严格解析判 invalid`
- **参考判断及来源**：—（格式失败；无参考标签语义）
- **观察到的失败**：模型把模板占位符连尖括号一起抄：`Label: <yes>` → 严格解析判 invalid（v1 ERR-008）
- **归类依据**：提示缺陷曾被误判为『模型不会遵循格式』→ 已证伪：语义标签完全正确，只是夹带尖括号（error_log 登记文本节选见 evidence 字段；原始试跑输出未保留——现 predictions_e2.jsonl 151 条、0 条含 '<yes>'，系修复后全量运行覆盖）
- **已有干预 / 仍未验证假说**：v1 修复 = 模板 v2 去掉尖括号占位符（Task A 模板冻结为 tpl_v2_20260920） / 占位符复述是否与模型规模相关 → 仅在 0.6B 上观察
- **产物路径**：`v1 docs/error_log.md（ERR-008 段落）+ runs/P2-baseline-20260920/predictions_e2.jsonl`
