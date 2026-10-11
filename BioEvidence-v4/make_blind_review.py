"""Same prespecified two questions across models; anonymous AI review stimuli."""
import argparse
import random
from common import *

def run(model,folder):
    dest=(ROOT/folder).resolve();assert dest.is_relative_to(ROOT/'ai_assisted')
    assert not (dest/'ratings_blinded.json').exists(),'Never overwrite locked review'
    rows=jsonl(ROOT/f'runs/{model}/smoke10/predictions.jsonl')
    ids=sorted({r['question_id'] for r in rows})[:2]
    selected=[r for r in rows if r['question_id'] in ids]
    assert len(selected)==8
    random.Random(20260924).shuffle(selected)
    cases=[];mapping=[]
    for i,r in enumerate(selected,1):
        key=f'AI{i+100:03d}'
        cases.append({'audit_id':key,'question':r['question'],
            'evidence':[{'display':f'E{j+1}','anonymous_chunk':hashlib.sha256(e['chunk_id'].encode()).hexdigest()[:12],
                         'section':e['section'],'text':e['text']} for j,e in enumerate(r['evidence'])],
            'output':r['raw_output']})
        mapping.append({'audit_id':key,'model':model,'question_id':r['question_id'],
                        'condition':r['condition'],'cache_key':r['cache_key']})
    write_json(dest/'blind_cases.json',cases)
    write_json(dest/'backend_mapping_locked.json',mapping)
    write_json(dest/'selection.json',{'selection':'Same first two sorted smoke questions as prior model, all conditions; no output-based selection',
        'n':8,'effective_questions':2,'presentation_seed':20260924,'prompt_version':'v4_ai_biomedical_audit_v1',
        'human_ground_truth':False,'prior_review_hidden':True})
    print('8 anonymous cases ready:',dest/'blind_cases.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--folder',required=True)
    a=p.parse_args();run(a.model,a.folder)
