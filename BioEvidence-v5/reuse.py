"""Reuse only verified sealed outputs; missing old generation telemetry stays unknown."""
from common import *
import adapter

def run():
    from transformers import AutoTokenizer
    assert read_json(ROOT/'reports/scoring_parity.json')['passed']
    docs={(d['question_id'],d['condition']):d for d in jsonl(ROOT/'data/dev151_conditions.jsonl')}
    checks=[]
    for key in ['base_06b','instruct_4b']:
        src=V4/f'runs/{key}/dev151/predictions.jsonl';rows=jsonl(src);assert len(rows)==604
        cfg=read_json(V4/f'runs/{key}/config.json')
        mp=(ROOT/read_json(ROOT/'config/models.json')[key]['path']).resolve()
        for name,sha in cfg['identity'].items():assert digest(mp/name)==sha,(key,name)
        for r in rows:
            d=docs[(r['question_id'],r['condition'])]
            for k in ['messages','evidence_block','chunk_order','display_to_chunk','gold']:assert r[k]==d[k],(key,k)
            parsed=adapter.score_one(d,r['raw_output'])
            for k in ['status','label','reason','answerable','citations','parse_note','citation_issues','error_codes']:assert r[k]==parsed[k]
            r['provenance']={'origin':'sealed_V4','source':str(src),'source_sha256':digest(src),'new_V5_generation':False}
        write_jsonl(ROOT/f'runs/{key}/dev151/predictions.jsonl',rows)
        write_jsonl(ROOT/f'runs/{key}/B0_dev151/predictions.jsonl',[r for r in rows if r['condition']=='B0_original'])
        write_json(ROOT/f'runs/{key}/config.json',cfg)
        checks.append({'model':key,'rows':604,'input_and_parse_and_weights':True,'source':str(src)})
    source=STAGEB/'predictions_order_dev.jsonl';old=jsonl(source);assert len(old)==604
    meta=read_json(STAGEB/'order_plan.json')['meta']
    assert meta['max_new_tokens']==160 and meta['prompt_fingerprint']==tb.template_fingerprint()
    mc=read_json(ROOT/'config/models.json')['e7_06b'];mp=(ROOT/mc['path']).resolve();ap=(ROOT/mc['adapter']).resolve()
    assert str(mp)==meta['model_path'] and str(ap)==meta['adapter_dir']
    frozen=read_json(V4/'runs/e7_06b/config.json')['identity']
    for name,sha in frozen.items():
        if name=='adapter':
            for file,hash_ in sha.items():assert digest(ap/file)==hash_
        else:assert digest(mp/name)==sha
    tok=AutoTokenizer.from_pretrained(str(mp),local_files_only=True);rows=[]
    p7={r['question_id']:r for r in jsonl(V1/'runs/P7-retrieval-20260921/predictions_e7_taskb_A2_quota.jsonl')}
    raw_b0_differences=[]
    for r in old:
        d=dict(docs[(r['question_id'],r['condition'])])
        for k in ['chunk_order','display_to_chunk','result_positions']:assert r[k]==d[k],k
        assert __import__('hashlib').sha256(d['evidence_block'].encode()).hexdigest()[:8]==r['block_sha8']
        d['rendered_prompt']=tok.apply_chat_template(d['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        d['input_token_ids']=tok(d['rendered_prompt'],add_special_tokens=False)['input_ids']
        assert len(d['input_token_ids'])==r['input_tokens'] and r['error'] is None
        parsed=adapter.score_one(d,r['raw_output'])
        for k in ['status','label','reason','answerable','citations','parse_note','citation_issues']:assert parsed[k]==r[k]
        if r['condition']=='B0_original' and r['raw_output']!=p7[r['question_id']]['raw_output']:raw_b0_differences.append(r['question_id'])
        rows.append({**parsed,'input_tokens':r['input_tokens'],'generated_tokens':None,'generated_token_ids':None,
            'output_retokenized_tokens':len(tok(r['raw_output'],add_special_tokens=False)['input_ids']),
            'generation_error':None,'finish_reason':'historical_not_recorded','output_budget_hit':None,
            'item_seconds':r['item_seconds'],'peak_allocated_gib':None,'peak_reserved_gib':None,'stop_sequences':None,
            'cache_hit':True,'cache_key':r['cache_config_key']+'|'+d['sample_id']+'|'+r['condition'],
            'config_fingerprint':fingerprint({'historical_config':meta,'weight_identity':frozen}),
            'provenance':{'origin':'sealed_V2_E7','source':str(source),'source_sha256':digest(source),
                'new_V5_generation':False,'backend':'historical direct Transformers; V4 verified 10 exact HF/harness/raw token regressions',
                'missing_telemetry':['generated_tokens','generated_token_ids','finish_reason','output_budget_hit','per_request_peak_memory']}})
    ref=read_json(STAGEB/'stageb_dev_analysis.json')['main_denominator_151']
    for cond in order.CONDITIONS:assert classification([r for r in rows if r['condition']==cond])==ref[cond]
    write_jsonl(ROOT/'runs/e7_06b/dev151/predictions.jsonl',rows)
    write_jsonl(ROOT/'runs/e7_06b/B0_dev151/predictions.jsonl',[r for r in rows if r['condition']=='B0_original'])
    write_json(ROOT/'runs/e7_06b/config.json',{'configuration':mc,'identity':frozen,'historical_meta':meta,'reuse':True})
    checks.append({'model':'e7_06b','rows':604,'input_parse_weights_frozen_metrics_verified':True,
        'B0_raw_difference_from_P7':raw_b0_differences,'telemetry_unknown_preserved':True})
    write_json(ROOT/'reports/reuse_integrity.json',{'passed':True,'checks':checks,'reused_rows':1812,
        'new_main_requests':604,'origins':'V4 raw1208 + V2 frozen E7 604; no regenerated model outputs',
        'reuse_boundary':'E7 runtime backend historical; missing telemetry explicitly unknown; exact V4 migration10 regression is supporting evidence, not 604 regenerated equivalence'})
    print('Reuse verified: 1812 historical rows; 604 new requests needed',flush=True)
if __name__=='__main__':run()
