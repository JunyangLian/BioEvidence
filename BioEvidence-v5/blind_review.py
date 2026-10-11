"""Fixed, balanced AI-assisted B0 cases; no model/condition/gold in reviewer packet."""
from common import *
from datetime import datetime,timezone
import random

def run():
    root=ROOT/'ai_assisted';assert not (root/'selection.json').exists(),'Selection is fixed once created'
    prior=sorted({r['question_id'] for r in jsonl(V4/'runs/base_06b/smoke10/predictions.jsonl')})[:2]
    refs=read_json(ROOT/'data/human_dev26_reference.json')
    selected=[min(r['question_id'] for r in refs if r['evidence_sufficiency']==s and r['question_id'] not in prior) for s in ['不足','充分']]
    payload=[]
    for i,qid in enumerate(selected):
        for m in ['base_06b','e7_06b','instruct_4b','tuned_4b']:
            r=next(r for r in jsonl(ROOT/f'runs/{m}/B0_dev151/predictions.jsonl') if r['question_id']==qid)
            payload.append((m,qid,{'anonymous_question_id':f'Q{i+1:02d}','question':r['question'],
                'evidence':[{'display_id':f'E{j+1}','chunk_id':e['chunk_id'],'section':e['section'],'text':e['text']} for j,e in enumerate(r['evidence'])],
                'raw_output':r['raw_output']}))
    random.Random(20261011).shuffle(payload);cases=[];mapping={}
    for i,(m,qid,r) in enumerate(payload):
        cid=f'R{i+1:02d}';r['case_id']=cid;cases.append(r);mapping[cid]={'model':m,'question_id':qid,'condition':'B0_original'}
    write_json(root/'blind_cases.json',cases)
    write_json(root/'private_mapping.json',mapping)
    write_json(root/'selection.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'selection':'First lexically sorted human-reference insufficient and sufficient questions, excluding the2 V4 AI review questions. Outputs did not determine selection.',
        'selected_question_ids_private':selected,'prior_excluded':prior,'n_questions':2,'n_cases':8,'reviews_per_case':2,
        'reviewer_model_balancing':'Each AI reviewer reviews all4 model groups; model labels/conditions/gold/human references and prior conclusions hidden',
        'shuffle_seed':20261011,'prompt_version':'v5_ai_biomedical_v1','human_truth':False,'packet_sha256':digest(root/'blind_cases.json'),
        'boundary':'Illustrative two-question subset; repeated questions may be recognized from content; stylistic blinding cannot be guaranteed; no prevalence or model superiority inference'})
    print('Blinded AI-assisted packet prepared: 8 cases/2 questions, balanced reviewers',flush=True)
if __name__=='__main__':run()
