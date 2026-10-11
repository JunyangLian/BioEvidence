"""Historical supervision statistics, distinct from semantic correctness."""
from common import *
from collections import Counter
import re

def run():
    rows=jsonl(ROOT/'data/sft_taskb_exact.jsonl');audit=[];labels=Counter();citations=Counter()
    for i,r in enumerate(rows):
        user=r['messages'][1]['content'];target=r['messages'][-1]['content']
        n=len(re.findall(r'^\[E\d+\]',user,re.M));parsed=tb.parse_output(target,n).to_dict()
        assert parsed['status']=='ok',('Historical target invalid',i)
        labels[(r['sample_type'],parsed['label'])]+=1
        for c in parsed['citations']:citations[f'E{c}']+=1
        audit.append({'record_index':i,'question_id':r['question_id'],'sample_type':r['sample_type'],
            'parsed_target':parsed,'n_evidence':n,'raw_target':target})
    report={'n_records':len(rows),'type_and_label':{'|'.join(k):v for k,v in labels.items()},
        'cited_display_position_counts':dict(citations),'yes_target_cites_only_E1':sum(r['sample_type']=='answerable_yes' and r['parsed_target']['citations']==[1] for r in audit),
        'semantic_label_validation':'Not performed; statistics do not establish evidence sufficiency, reason support or target correctness',
        'source_sha256':digest(ROOT/'data/sft_taskb_exact.jsonl'),'all_targets_parse':True,
        'interpretation':'Raw targets retained. Position distribution is a possible mechanism to investigate, not a causal conclusion about order sensitivity.'}
    write_json(ROOT/'reports/historical_target_distribution.json',report)
    write_jsonl(ROOT/'data/target_parse_audit.jsonl',audit)
    print(report,flush=True)
if __name__=='__main__':run()
