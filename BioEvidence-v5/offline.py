"""True frozen-dev parity through harness evaluator, with zero model calls."""
from common import *
from adapter import *

FIELDS=('status','label','reason','answerable','citations','parse_note','citation_issues')

def run():
    from lm_eval.api.model import LM
    from lm_eval import evaluator
    from transformers import AutoTokenizer
    docs=jsonl(ROOT/'data/dev151_conditions.jsonl')
    tok=AutoTokenizer.from_pretrained(str(V1/'artifacts/models/Qwen3-0.6B'),local_files_only=True)
    for doc in docs:
        doc['rendered_prompt']=tok.apply_chat_template(doc['messages'], tokenize=False,
            add_generation_prompt=True,enable_thinking=False)
    original=jsonl(STAGEB/'predictions_order_dev.jsonl')
    stored={(r['question_id'],r['condition']):r for r in original}
    class Replay(LM):
        def __init__(self): super().__init__()
        def generate_until(self, requests):
            return [stored[(r.doc['question_id'],r.doc['condition'])]['raw_output'] for r in requests]
        def loglikelihood(self,requests): raise NotImplementedError
        def loglikelihood_rolling(self,requests): raise NotImplementedError
    # Independent frozen artifacts are A. B traverses actual harness process_results/aggregation.
    task=make_task(docs,name='bioevidence_offline_replay')
    result=evaluator.simple_evaluate(model=Replay(),tasks=[task],num_fewshot=0,
        bootstrap_iters=0,log_samples=True,apply_chat_template=False,random_seed=20260924,
        numpy_random_seed=20260924,torch_random_seed=20260924)
    write_json(ROOT/'runs/offline/harness_results.json',result)
    samples=result['samples']['bioevidence_offline_replay']
    adapted=[]
    diffs=[]
    for sample in samples:
        doc=sample['doc']; key=(doc['question_id'],doc['condition']); a=stored[key]
        raw=sample['resps'][0][0]
        b=score_one(doc,raw); adapted.append(b)
        for field in FIELDS:
            if a[field]!=b[field]: diffs.append({'key':key,'field':field,'historical':a[field],'adapted':b[field]})
        # The historical schema has status/parse_note/citation_issues, not a
        # separate error_codes field. Map only its existing codes for comparison.
        historical_codes=([a['status']] if a['status']!='ok' else [])+a['citation_issues']
        if historical_codes!=b['error_codes']:
            diffs.append({'key':key,'field':'error_codes','historical':historical_codes,'adapted':b['error_codes']})
        if raw!=a['raw_output']: diffs.append({'key':key,'field':'raw_output'})
    reference=read_json(STAGEB/'stageb_dev_analysis.json')['main_denominator_151']
    per={}
    for cond in order.CONDITIONS:
        rs=[r for r in adapted if r['condition']==cond]
        actual=classification(rs)
        assert actual==reference[cond],(cond,'historical v2 frozen summary mismatch')
        per[cond]={'A_frozen_v2':reference[cond],'B_harness_adapted':actual,'exact_equal':True}
    # Separately validate v1 mapping against P7 frozen metric, same B0 raw dev outputs.
    v1rows=jsonl(V1/'runs/P7-retrieval-20260921/predictions_e7_taskb_A2_quota.jsonl')
    bydoc={d['question_id']:d for d in docs if d['condition']=='B0_original'}
    v1adapt=[score_one(bydoc[r['question_id']],r['raw_output']) for r in v1rows]
    frozen_v1=read_json(V1/'runs/P7-retrieval-20260921/metrics_e7_taskb_A2_quota.json')
    migrated_v1=classification(v1adapt,'v1')
    v1checks={k:migrated_v1[k]==frozen_v1[k] for k in migrated_v1 if k in frozen_v1}
    assert all(v1checks.values()),v1checks
    v1_parse_differences=[]
    for original_row,adapted_row in zip(v1rows,v1adapt):
        for field in FIELDS:
            if original_row[field]!=adapted_row[field]:
                v1_parse_differences.append({'question_id':original_row['question_id'],'field':field})
    from legacy_structural import structural
    v1_structural=structural([{**a,'gold_answerable':o['gold_answerable'],
        'idx_to_doc':o['idx_to_doc']} for o,a in zip(v1rows,v1adapt)])
    assert v1_structural==frozen_v1['citation_structural_checks'],'Historical v1 structural counts/denominators mismatch'
    assert not v1_parse_differences,v1_parse_differences
    # Citation and Answerable mechanical counts independent of adapted reference.
    def counts(rows):
        return {c:{'n':len([r for r in rows if r['condition']==c]),
            'parse_status':{s:sum(r['condition']==c and r['status']==s for r in rows) for s in ('ok','invalid','invalid_citation')},
            'answerable':{s:sum(r['condition']==c and r['answerable']==s for r in rows) for s in ('yes','no',None)},
            'cited_rows':sum(r['condition']==c and bool(r['citations']) for r in rows),
            'citation_issues':sum(r['condition']==c and bool(r['citation_issues']) for r in rows),
            'citations_total':sum(len(r['citations']) for r in rows if r['condition']==c)} for c in order.CONDITIONS}
    mechanical_a=counts(original); mechanical_b=counts(adapted)
    assert mechanical_a==mechanical_b
    combined=classification(adapted)
    harness_metrics=result['results']['bioevidence_offline_replay']
    assert harness_metrics['bio_accuracy,none']==combined['accuracy']
    assert harness_metrics['bio_macro_f1,none']==combined['macro_f1']
    write_jsonl(ROOT/'runs/offline/parsed_rows.jsonl',adapted)
    report={'passed':not diffs,'real_development_raw_outputs':604,'model_calls':0,
        'reference_A':'independent historical frozen v2 predictions + stageb_dev_analysis.json; v1 P7 predictions + metrics',
        'route_B':'lm_eval evaluator -> generate_until replay -> Task.process_results -> custom aggregation',
        'parse_fields_compared':FIELDS,'differences':diffs,'per_condition':per,
        'error_code_comparison':'604 exact; historical status + citation_issues mapped losslessly (parse_note also compared); no separate historical error_codes field',
        'v1_frozen_checks':v1checks,'v1_score':migrated_v1,
        'v1_parse_differences':v1_parse_differences,'v1_structural_checks':v1_structural,
        'v1_structural_route':'exact AST statements from frozen eval_taskb.main; compared to independent P7 frozen summary',
        'mechanical_reference':mechanical_a,'mechanical_adapted':mechanical_b,
        'aggregate':combined,'harness_metrics':harness_metrics,
        'note':'Replay is actual historical-output scoring, not new model generation; synthetic risks are separate.'}
    write_json(ROOT/'reports/scoring_parity.json',report)
    assert not diffs,diffs
    print('REAL offline scoring parity PASSED: 604 dev outputs, four conditions; v1 B0 151',flush=True)

if __name__=='__main__': run()
