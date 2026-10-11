"""Final read-only checks of real outputs, source assembly, cache and old scores."""
import argparse
from datetime import datetime, timezone
from common import *

def run(scope='dev151'):
    from transformers import AutoTokenizer
    source={(d['question_id'],d['condition']):d for d in jsonl(ROOT/'data/dev151_conditions.jsonl')}
    configs=read_json(ROOT/'config/models.json'); checks={}
    for model_key in ('base_06b','instruct_4b'):
        folder=ROOT/'runs'/model_key/scope
        rows=jsonl(folder/'predictions.jsonl'); summary=read_json(folder/'summary.json')
        keys={(r['question_id'],r['condition']) for r in rows}
        assert len(keys)==len(rows)==(604 if scope=='dev151' else 40)
        if scope=='dev151':assert keys==set(source)
        cfg=configs[model_key]
        tok=AutoTokenizer.from_pretrained(str((ROOT/cfg['path']).resolve()),local_files_only=True)
        for r in rows:
            d=source[(r['question_id'],r['condition'])]
            assert all(r[k]==v for k,v in d.items()),'Source data/evidence/reference changed'
            kwargs={'enable_thinking':False} if cfg['thinking'] is False else {}
            rendered=tok.apply_chat_template(d['messages'],tokenize=False,add_generation_prompt=True,**kwargs)
            assert rendered==r['rendered_prompt']
            ids=tok(rendered,add_special_tokens=False)['input_ids']
            assert ids==r['input_token_ids'] and len(ids)==r['input_tokens']
            assert len(ids)+configs['shared']['max_new_tokens']<=configs['shared']['max_length']
            assert len(r['generated_token_ids'])==r['generated_tokens']
            old=tb.parse_output(r['raw_output'],n_evidence=len(d['chunk_order'])).to_dict()
            for field in ('label','reason','answerable','citations','parse_note','citation_issues'):
                assert r[field]==old[field],(model_key,r['sample_id'],field)
            assert old['status']==r['parsed_status']
            assert r['status']==('invalid' if r['generation_error'] else old['status'])
            errors=([old['status']] if old['status']!='ok' else [])+old['citation_issues']+([r['generation_error']] if r['generation_error'] else [])
            assert errors==r['error_codes']
            cache=ROOT/'cache/generation'/model_key/r['config_fingerprint']/(r['cache_key']+'.json')
            original=read_json(cache)
            assert {k:v for k,v in r.items() if k!='cache_hit'}=={k:v for k,v in original.items() if k!='cache_hit'}
            assert r['config_fingerprint']==summary['config_fingerprint']
        scores=classification(rows)
        harness=summary['harness_results']['bioevidence_taskb']
        actual_backend=read_json(folder/'harness_results.json')['config']
        assert scores['accuracy']==harness['bio_accuracy,none']
        assert scores['macro_f1']==harness['bio_macro_f1,none']
        invalid=sum(r['status']!='ok' for r in rows)
        assert invalid/len(rows)==harness['bio_invalid_rate,none']
        checks[model_key]={'n_checked':len(rows),'source_prompt_and_tokens_unchanged':True,
            'raw_and_entire_record_match_cache':True,'historical_parser_fields_and_errors_match':True,
            'actual_harness_aggregation_matches_historical_entry':True,
            'cache_hits':sum(r['cache_hit'] for r in rows),'fresh_requests':sum(not r['cache_hit'] for r in rows),
            'runtime_failure_count':sum(bool(r['generation_error']) for r in rows),
            'parsed_non_ok_count':sum(r['parsed_status']!='ok' for r in rows),
            'actual_harness_model_dtype':actual_backend['model_dtype'],
            'actual_harness_model_num_parameters':actual_backend['model_num_parameters'],
            'local_revision_note':'Harness model_revision main is a local-loader default, not provenance. Full identity hashes are in runs/model/config.json; 4B upstream revision is in its verified download_manifest.json.'}
    report={'passed':True,'scope':scope,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'model_calls':0,'checks':checks,'note':'Validates records, without replacing failures or modifying raw outputs.'}
    write_json(ROOT/f'reports/output_integrity_{scope}.json',report)
    print('Actual output integrity passed:',checks)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',default='dev151',choices=['dev151','smoke10']);a=p.parse_args();run(a.scope)
