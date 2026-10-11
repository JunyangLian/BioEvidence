"""Summarize locked AI opinions without promoting them to human truth."""
from common import *

def run():
    folders=[ROOT/'ai_assisted',ROOT/'ai_assisted/batch2']
    batches=[]; opinions=[]
    for folder in folders:
        lock=read_json(folder/'audit_lock.json')
        assert digest(folder/'ratings_blinded.json')==lock['sha256']
        summary=read_json(folder/'summary.json')
        rows=read_json(folder/'ratings_unsealed.json')
        assert summary['human_ground_truth'] is False and len(rows)==8
        models={r['backend']['model'] for r in rows}; assert len(models)==1
        model=next(iter(models))
        batches.append({'model':model,'agent':summary['metadata']['agent'],
            'model_identifier':summary['metadata']['model_identifier'],
            'rating_sha256':lock['sha256'],'validated_quote_locations':lock['validated_quote_locations'],
            'counts':summary['counts'],'n_opinions':len(rows)})
        opinions.extend(rows)
    questions=sorted({r['backend']['question_id'] for r in opinions})
    assert len(questions)==2 and len(opinions)==16
    evidence_agreement={q:sorted({r['evidence_sufficiency'] for r in opinions if r['backend']['question_id']==q}) for q in questions}
    result={'review_kind':'ai_assisted','human_ground_truth':False,'n_opinions':16,
        'n_unique_questions':2,'n_agents':2,'validated_quote_locations':48,'batches':batches,
        'evidence_sufficiency_opinions_by_question':evidence_agreement,
        'limitations':['Convenience first-two-question selection, not representative',
            'Different agents reviewed different models: reviewer and model are confounded',
            'No inference of model superiority, population prevalence or human correctness',
            'Unknown and N_A remain distinct and are never converted to passing',
            'Reason text is not direct evidence of model internal reasoning',
            'Chunk traceability does not imply semantic support or source-document verification']}
    write_json(ROOT/'ai_assisted/cross_model_summary.json',result)
    fields=['evidence_sufficiency','evidence_supports_reason','reason_supports_label',
        'citation_traceability','citation_support','abstention_appropriateness']
    lines=['# AI 辅助语义案例复核','',
        '两批盲审均先锁定意见、核验逐字定位，再解封条件映射。共16条输出、2道开发题、2个当前任务内AI子agent、48处证据定位。精确agent模型标识不可取得，原样记录unknown。不是实际专家审核或独立人工真值。','',
        '| 维度 | 0.6B输出对应AI意见（8条） | 4B输出对应AI意见（8条） |',
        '|---|---|---|']
    for f in fields:
        cells=['; '.join(f'{k}={v}' for k,v in b['counts'][f].items()) for b in batches]
        lines.append(f'| {f} | {cells[0]} | {cells[1]} |')
    lines+=['','此表记录原始意见分布，不计算通过率。N_A和unknown不能记作通过；每个问题在四条件下重复，不能当成16道独立问题。',
        '两批对证据充分性的意见在同题上一致，但Reason支持、引用支持等判断针对不同输出，且审核agent与模型配置混杂，不能据此宣布跨模型优劣。',
        '案例10411439：两批均认为所给片段不足以回答目标体位问题；合法引用仍可能只支持相关背景。4B在部分顺序下弃答，而另一些顺序下作答；这是个案行为观察。',
        '案例10593212：两批均认为证据足以支持给定研究的比较方向；显著性或阴性结果仍不自动证明普遍无效、等效或安全。',
        '审核仅依据给定片段和可见输出；引用可回溯性只核对显示编号至匿名片段，外部文献来源核验为unknown。输出Reason不是内部推理过程的直接证据。意见不回写历史人工标签。',
        '原始盲化意见与锁定SHA分别见ratings_blinded.json、batch2/ratings_blinded.json及对应audit_lock.json；解封记录与逐条件评定另存ratings_unsealed.json。']
    (ROOT/'ai_assisted/AI_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Locked AI summaries joined: 16 opinions / 2 questions / 48 quote locations')

if __name__=='__main__':run()
