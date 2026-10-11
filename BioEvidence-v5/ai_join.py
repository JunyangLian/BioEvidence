"""Lock blinded AI opinions and exact evidence quotes before joining private model map."""
from common import *
from datetime import datetime,timezone
from collections import Counter

FIELDS=['evidence_sufficiency','reason_key_claim_support','reason_label_alignment','citation_traceability','citation_semantic_support','abstention_appropriateness']
VALUES=[
    {'sufficient','insufficient','unknown'},{'supported','partial','unsupported','unknown'},
    {'supported','partial','unsupported','unknown'},{'traceable','not_traceable','unknown','N_A'},
    {'supported','partial','unsupported','unknown','N_A'},{'appropriate','inappropriate','unknown'}]

def run():
    root=ROOT/'ai_assisted';packet=read_json(root/'blind_cases.json');cases={r['case_id']:r for r in packet}
    selection=read_json(root/'selection.json');assert digest(root/'blind_cases.json')==selection['packet_sha256']
    reports=[];quote_count=0
    for filename in ['review_a_blinded.json','review_b_blinded.json']:
        p=root/filename;r=read_json(p);assert r['audit_kind']=='ai_assisted' and r['prompt_version']==selection['prompt_version']
        assert len(r['records'])==8 and {x['case_id'] for x in r['records']}==set(cases)
        assert r['actual_model_identifier'] in ['unknown/unavailable','unknown','unavailable'],'Actual runtime model identity must be obtained, not inferred'
        for row in r['records']:
            for f,valid in zip(FIELDS,VALUES):
                assert row[f] in valid,(filename,row['case_id'],f,row[f])
                assert row['rationale'][f],(filename,row['case_id'],f,'missing rationale')
            assert isinstance(row['reservations'],list)
            evidence={e['display_id']:e for e in cases[row['case_id']]['evidence']}
            for loc in row['evidence_locations']:
                e=evidence[loc['display_id']];assert e['chunk_id']==loc['chunk_id']
                assert loc['quote'] and loc['quote'] in e['text'],(filename,row['case_id'],'quote not exact',loc['quote'])
                quote_count+=1
        reports.append(r)
    lockpath=root/'audit_lock.json'
    hashes={p:digest(root/p) for p in ['blind_cases.json','RUBRIC.md','review_a_blinded.json','review_b_blinded.json']}
    if lockpath.exists():assert read_json(lockpath)['hashes']==hashes,'Locked blinded review changed'
    else:
        write_json(lockpath,{'locked_at_utc':datetime.now(timezone.utc).isoformat(),'hashes':hashes,
            'n_opinions':16,'n_questions':2,'exact_quote_locations':quote_count,'models_conditions_gold_not_given_to_reviewers':True,
            'before_joining_model_map':True,'audit_kind':'ai_assisted','human_truth':False})
        for p in ['blind_cases.json','RUBRIC.md','review_a_blinded.json','review_b_blinded.json','audit_lock.json']:(root/p).chmod(0o444)
    # The only unsealing step occurs after the lock exists and quote/schema validation.
    mapping=read_json(root/'private_mapping.json');joined=[];transitions=[]
    for review in reports:
        by={}
        for row in review['records']:
            meta=mapping[row['case_id']]
            joined.append({**row,**meta,'agent_task':review['agent_task'],'actual_model_identifier':review['actual_model_identifier'],
                'timestamp_utc':review['timestamp_utc'],'audit_kind':'ai_assisted','prompt_version':review['prompt_version']})
            by[(meta['question_id'],meta['model'])]=row
        for q in sorted({m['question_id'] for m in mapping.values()}):
            for a,b in [('base_06b','e7_06b'),('instruct_4b','tuned_4b')]:
                x,y=by[(q,a)],by[(q,b)]
                transitions.append({'question_id':q,'agent_task':review['agent_task'],'untuned':a,'tuned':b,
                    'transitions':{f:f'{x[f]} -> {y[f]}' for f in FIELDS}})
    r0={r['case_id']:r for r in reports[0]['records']};r1={r['case_id']:r for r in reports[1]['records']}
    disagreement={f:{'disagree':sum(r0[c][f]!=r1[c][f] for c in cases),'den_cases':8} for f in FIELDS}
    summary={'audit_kind':'ai_assisted','human_truth':False,'n_questions':2,'n_unique_cases':8,'n_opinions':16,
        'exact_evidence_quote_locations':quote_count,'both_reviewers_evaluated_all4_models':True,'conditions':'B0 only',
        'actual_model_identifiers':[r['actual_model_identifier'] for r in reports],
        'unknown_or_NA':{f:sum(row[f] in ['unknown','N_A'] for row in joined) for f in FIELDS},
        'reviewer_disagreement':disagreement,'within_reviewer_transitions':transitions,
        'limits':['AI simulation, not real biomedical experts or independent human review','Only2 reference-stratified development questions',
            'No prevalence or model superiority inference','Stylish outputs and question repetition limit blinding',
            'Outputs are reasons, not internal reasoning evidence','Human references/gold were hidden and not rewritten'],
        'locked_review_sha256':digest(lockpath)}
    write_jsonl(root/'ratings_unsealed.jsonl',joined);write_json(root/'summary.json',summary)
    lines=['# V5 AI辅助语义案例复核','',
        '两位当前任务内AI子agent各自评完四组模型的同样2题B0，共16条意见。选择依据为人工参考充分/不足各一题的字典序第一题，排除V4此前两题；没有按模型输出挑题。模型/条件/旧标签/人工参考/前次审核隐藏，完整原始输出及实际片段保留；风格和重复问题可能削弱盲化。',
        f'实际agent模型运行标识均无法取得，记录unknown/unavailable。锁定前逐条校验8案例×2、6项枚举、理由和{quote_count}处原文短引文及稳定chunk定位。锁定文件及时间见audit_lock.json；之后才按private_mapping配对汇总。',
        '','这是AI辅助的专家视角模拟，不是真实专家、独立人工真值或整体模型能力评估。仅2题，不能用百分比外推、宣布语义收益或支持模型优劣。两审核者均覆盖全部四组，减少审核者与模型的完全混杂，但不代表独立人类判断。',
        '','| agent | 问题 | 微调前→后 | 证据充分性 | 理由关键主张支持 | 理由与标签一致 | 引用语义支持 | 作答/弃答恰当 |',
        '|---|---|---|---|---|---|---|---|']
    for r in transitions:
        t=r['transitions'];lines.append(f"| {r['agent_task']} | {r['question_id']} | {r['untuned']}→{r['tuned']} | {t['evidence_sufficiency']} | {t['reason_key_claim_support']} | {t['reason_label_alignment']} | {t['citation_semantic_support']} | {t['abstention_appropriateness']} |")
    lines+=['','Unknown/N_A与保留意见保留，未自动记通过。无RESULTS不自动不足，有RESULTS不自动充分；非显著不等于无效/等效/安全。完整意见、分歧、机械可回溯与语义支持区别见ratings_unsealed.jsonl及summary.json。原人工标签未回写。']
    (root/'AI_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('AI-assisted opinions locked and unsealed',quote_count,'exact quote locations',flush=True)
if __name__=='__main__':run()
