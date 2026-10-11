"""Auditable V5 runner forks: unchanged scoring, explicit scope and missing telemetry."""
from common import *
import importlib.metadata as md
import subprocess

def replace(s,a,b):
    assert a in s,('Frozen source changed',a);return s.replace(a,b)

def run():
    s=(V4/'generate.py').read_text(encoding='utf-8')
    s=replace(s,'def run(model_key, n=10, regression=False):','def run(model_key, n=10, regression=False, conditions=None):')
    s=replace(s,"('.json','.safetensors','.txt')","('.json','.safetensors','.txt','.jinja')")
    s=replace(s,"'runner_code':digest(ROOT/'generate.py')})",
        "'runner_code':digest(ROOT/'generate.py'),'common_code':digest(ROOT/'common.py'),\n        'historical_parser':digest(V1/'src/bioevidence/inference/prompts_taskb.py'),\n        'historical_scorer':digest(V2/'scripts/v2_stageb_dev_analysis.py')})")
    s=replace(s,"(model_key!='e7_06b' or d['condition']=='B0_original')","(not conditions or d['condition'] in conditions)")
    s=replace(s,"('dev151' if n==151 else 'smoke10')","(('B0_dev151' if conditions else 'dev151') if n==151 else 'smoke10')")
    s=replace(s,"['base_06b','instruct_4b','e7_06b']","['base_06b','instruct_4b','e7_06b','tuned_4b']")
    s=replace(s,"a=ap.parse_args()","ap.add_argument('--b0-only',action='store_true'); a=ap.parse_args()")
    s=replace(s,'run(a.model,a.n,a.regression)',"run(a.model,a.n,a.regression,['B0_original'] if a.b0_only else None)")
    (ROOT/'generate.py').write_text(s,encoding='utf-8')
    s=(V4/'analyze.py').read_text(encoding='utf-8')
    s=replace(s,'if not nums:return None','nums=[x for x in nums if x is not None]\n    if not nums:return None')
    s=replace(s,"sum(r['output_budget_hit'] for r in rs)","sum(r['output_budget_hit'] is True for r in rs)")
    s=replace(s,"'output_tokens':distribution", "'historical_missing_stop_or_budget_telemetry':sum(r['output_budget_hit'] is None for r in rs),\n            'actual_generated_token_count_coverage':ratio(sum(r['generated_tokens'] is not None for r in rs),len(rs)),\n            'output_retokenized_count':distribution([r.get('output_retokenized_tokens') for r in rs]),\n            'output_tokens':distribution")
    for field in ['peak_allocated_gib','peak_reserved_gib']:
        for rows in ['rs','rows']:
            s=replace(s,f"max(r['{field}'] for r in {rows})",f"max((r['{field}'] for r in {rows} if r['{field}'] is not None),default=None)")
    s=replace(s,"sum(r['generated_tokens'] for r in rows)","sum(r['generated_tokens'] for r in rows if r['generated_tokens'] is not None) if any(r['generated_tokens'] is not None for r in rows) else None")
    s=replace(s,"sum(not r['cache_hit'] for r in rows)","sum(not r['cache_hit'] and not r.get('provenance') for r in rows)")
    s=replace(s,"'requests':len(rows)","'requests':len(rows),'new_V5_requests':sum(r.get('provenance',{}).get('origin') is None for r in rows),\n        'actual_generated_token_count_known_rows':sum(r['generated_tokens'] is not None for r in rows)")
    (ROOT/'analyze.py').write_text(s,encoding='utf-8')
    versions={d.metadata['Name']:d.version for d in md.distributions()}
    (ROOT/'requirements-lock.txt').write_text('\n'.join(f'{k}=={v}' for k,v in sorted(versions.items()))+'\n',encoding='utf-8')
    req=[]
    for p in [ROOT/'install-baseline-report.json',ROOT/'install-trl-report.json']:
        for d in read_json(p)['install']:
            sha=d['download_info']['archive_info']['hashes']['sha256']
            req.append(f"{d['metadata']['name']}=={d['metadata']['version']} --hash=sha256:{sha}")
    (ROOT/'requirements-hashed.txt').write_text('\n'.join(sorted(set(req)))+'\n',encoding='utf-8')
    import torch,transformers,trl,bitsandbytes,peft,lm_eval
    baseline=read_json(V4/'install-snapshot-report.json')
    changes=[]
    for d in baseline['install']:
        name=d['metadata']['name'];expected=d['metadata']['version'];actual=md.version(name)
        if actual!=expected:changes.append([name,expected,actual])
    assert not changes,changes
    assert sys.prefix==str(ROOT/'.venv') and not __import__('site').ENABLE_USER_SITE
    srcs=[Path(transformers.__file__),Path(trl.__file__).parent/'trainer/sft_trainer.py',Path(peft.__file__),Path(lm_eval.__file__)]
    write_json(ROOT/'environment.json',{'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,
        'isolated':True,'core_baseline_unchanged':True,'packages':versions,'cuda':torch.version.cuda,
        'gpu':torch.cuda.get_device_name(0),'gpu_memory_bytes':torch.cuda.get_device_properties(0).total_memory,
        'source_hashes':{str(p):digest(p) for p in srcs},'source_commits':{'TRL':None,'note':'Official PyPI wheel provenance and complete SHA256 installation reports; no source Git checkout'},
        'upstream_documentation':['https://huggingface.co/docs/trl/sft_trainer','https://huggingface.co/docs/transformers/quantization/bitsandbytes'],
        'runner_forks':{p:{'source':str(V4/p),'source_sha256':digest(V4/p),'v5_sha256':digest(ROOT/p)} for p in ['generate.py','analyze.py','adapter.py','offline.py']},
        'fork_changes':'Generation adds tuned4B/condition scope and .jinja/common/frozen parser/scorer identity. V5 JSON writes atomic. Analysis separates historical costs and unknown telemetry with coverage; frozen parsing/classification unchanged.'})
    print('Independent runtime locked; baseline versions unchanged',flush=True)
if __name__=='__main__':run()
