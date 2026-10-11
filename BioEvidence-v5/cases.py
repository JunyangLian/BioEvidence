"""Mechanical adaptation casebook; fixed lexical ordering, no semantic grading."""
from common import *
from analyze import correct,cited,strict_issues
from collections import defaultdict

def run():
    refs={r['question_id']:r for r in read_json(ROOT/'data/human_dev26_reference.json')}
    cases=[];examples=defaultdict(list)
    for raw,tuned in [('base_06b','e7_06b'),('instruct_4b','tuned_4b')]:
        a={(r['question_id'],r['condition']):r for r in jsonl(ROOT/f'runs/{raw}/dev151/predictions.jsonl')}
        b={(r['question_id'],r['condition']):r for r in jsonl(ROOT/f'runs/{tuned}/dev151/predictions.jsonl')}
        for key in sorted(a):
            x,y=a[key],b[key];types=[]
            if correct(x) and not correct(y):types.append('classification_regression')
            if not correct(x) and correct(y):types.append('classification_gain')
            if not strict_issues(x) and strict_issues(y):types.append('mechanical_contract_introduced')
            if strict_issues(x) and not strict_issues(y):types.append('mechanical_contract_resolved')
            ref=refs.get(key[0])
            if ref:
                if ref['evidence_sufficiency']=='不足' and y['status']=='ok' and y['answerable']=='yes':types.append('still_answers_human_insufficient')
                if ref['evidence_sufficiency']=='充分' and y['status']=='ok' and y['answerable']=='no':types.append('abstains_human_sufficient')
            if not types:continue
            r={'question_id':key[0],'condition':key[1],'pair':[raw,tuned],'types':types,
                'question':x['question'],'evidence':x['evidence'],'evidence_block':x['evidence_block'],
                'display_to_chunk':x['display_to_chunk'],'gold_question_label':x['gold'],
                'human_sufficiency':ref or None,'semantic_support_grade':'not_assigned_by_mechanical_casebook; separate limited AI opinions in ai_assisted',
                'untuned':{k:x[k] for k in ['raw_output','label','answerable','citations','status','error_codes']},
                'tuned':{k:y[k] for k in ['raw_output','label','answerable','citations','status','error_codes']},
                'actual_cited_chunks':{'untuned':sorted(cited(x)),'tuned':sorted(cited(y))}}
            cases.append(r)
            for typ in types:
                tag=raw+'->'+tuned+'|'+typ
                if len(examples[tag])<2:examples[tag].append({'question_id':key[0],'condition':key[1]})
    write_jsonl(ROOT/'reports/adaptation_cases_all.jsonl',cases)
    write_json(ROOT/'reports/adaptation_case_index.json',{'selection':'First two lexically ordered question/condition per pair and mechanical category; all qualifying cases retained separately',
        'n_records':len(cases),'illustrative_index':dict(examples),
        'boundary':'Gold-label correctness does not establish evidence support. Mechanical casebook has no semantic grades; limited two-question AI-assisted opinions are separate.'})
    print('Mechanical casebook',len(cases),'records',flush=True)
if __name__=='__main__':run()
