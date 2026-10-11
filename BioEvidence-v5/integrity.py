"""Actual generation artifacts, frozen parser and harness aggregate checks."""
from common import *
import adapter

def run(scope='dev151',models=None):
    from transformers import AutoTokenizer
    configs=read_json(ROOT/'config/models.json')
    docs={(d['question_id'],d['condition']):d for d in jsonl(ROOT/'data/dev151_conditions.jsonl')}
    checks={}
    for m in models or ['base_06b','e7_06b','instruct_4b','tuned_4b']:
        path=ROOT/f'runs/{m}/{scope}/predictions.jsonl';rows=jsonl(path)
        keys={(r['question_id'],r['condition']) for r in rows};assert len(keys)==len(rows)
        if scope=='dev151':assert keys==set(docs) and len(rows)==604
        if scope=='B0_dev151':assert len(rows)==151 and all(r['condition']=='B0_original' for r in rows)
        cfg=configs[m];tok=AutoTokenizer.from_pretrained(str((ROOT/cfg['path']).resolve()),local_files_only=True)
        for r in rows:
            d=docs[(r['question_id'],r['condition'])]
            assert all(r[k]==v for k,v in d.items()),(m,'Source changed')
            opts={'enable_thinking':False} if cfg['thinking'] is False else {}
            prompt=tok.apply_chat_template(d['messages'],tokenize=False,add_generation_prompt=True,**opts)
            assert prompt==r['rendered_prompt'] and tok(prompt,add_special_tokens=False)['input_ids']==r['input_token_ids']
            assert len(r['input_token_ids'])==r['input_tokens'] and r['input_tokens']+160<=2048
            adapter.RUNTIME[(r['question_id'],r['condition'])]=r
            parsed=adapter.score_one(d,r['raw_output'])
            for k in ['status','label','reason','answerable','citations','parse_note','citation_issues','error_codes','parsed_status']:assert r[k]==parsed[k],(m,k)
            if not r.get('provenance'):
                assert len(r['generated_token_ids'])==r['generated_tokens']
                cached=read_json(ROOT/f"cache/generation/{m}/{r['config_fingerprint']}/{r['cache_key']}.json")
                assert {k:v for k,v in r.items() if k!='cache_hit'}=={k:v for k,v in cached.items() if k!='cache_hit'}
        if m=='tuned_4b':
            summary=read_json(path.parent/'summary.json');hr=summary['harness_results']['bioevidence_taskb']
            cl=classification(rows);assert cl['accuracy']==hr['bio_accuracy,none'] and cl['macro_f1']==hr['bio_macro_f1,none']
            assert sum(r['status']!='ok' for r in rows)/len(rows)==hr['bio_invalid_rate,none']
            assert len({r['config_fingerprint'] for r in rows})==1
        checks[m]={'rows':len(rows),'exact_prompts_and_tokens_and_frozen_parse':True,
            'generation_exceptions':sum(r['finish_reason']=='exception' for r in rows),
            'budget_hits_known':sum(r['output_budget_hit'] is True for r in rows),
            'budget_unknown_rows':sum(r['output_budget_hit'] is None for r in rows),
            'historical_origin_rows':sum(bool(r.get('provenance')) for r in rows),
            'harness_aggregate_checked':m=='tuned_4b','source_sha256':digest(path)}
    report={'passed':True,'scope':scope,'checks':checks,'model_calls':0}
    write_json(ROOT/f'reports/output_integrity_{scope}.json',report);print('Output integrity passed',scope,checks,flush=True)
    return report
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--scope',default='dev151');p.add_argument('--only-tuned',action='store_true');a=p.parse_args()
    run(a.scope,['tuned_4b'] if a.only_tuned else None)
