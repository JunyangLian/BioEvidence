"""Continue gated model smokes, fixed dev expansion, reports and protection checks."""
import subprocess
import time
import argparse
from datetime import datetime, timezone
from common import *

def event(kind,details):
    row={'event':kind,'details':details,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
    p=ROOT/'logs/pipeline_events.jsonl';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf-8') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(kind,details,row['timestamp_utc'],flush=True)

def command(script,*args):
    name=script.removesuffix('.py')+'_'+('_'.join(args).replace('--','') or 'run')
    path=ROOT/'logs'/f'{name}.log';path.parent.mkdir(parents=True,exist_ok=True)
    event('START',[script,*args])
    with path.open('w',encoding='utf-8') as out:
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/script),*args],stdout=out,stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,f'{script} failed: {path}'
    event('DONE',[script,*args])

def run():
    command('generate.py','--model','instruct_4b','--n','10')
    command('analyze.py','--model','instruct_4b','--scope','smoke10')
    costs={}
    for m in ['base_06b','instruct_4b']:
        smoke=read_json(ROOT/f'runs/{m}/smoke10/summary.json')
        assert smoke['input_system_and_context_checks_passed'] and smoke['n']==40 and smoke['generation_exceptions']==0
        # Format failures and budget hits remain recorded outcomes; do not tune to improve scores.
        analysis=read_json(ROOT/f'runs/{m}/smoke10/analysis.json')
        sec=analysis['cost']['generation_seconds_all_unique']/40
        costs[m]={'remaining_requests':564,'measured_mean_seconds':sec,'projected_remaining_generation_seconds':564*sec,
                  'smoke_output_budget_hits':smoke['output_budget_hits'],'locked_config_fingerprint':smoke['config_fingerprint']}
    write_json(ROOT/'reports/expansion_cost_plan.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'main_unique_requests':1208,'smoke_unique_requests':80,'remaining_requests':1128,'models':costs,
        'note':'Actual measured smoke cost; load overhead separate; cached completed samples reused.'})
    event('EXPANSION',costs)
    for m in ['base_06b','instruct_4b']:command('generate.py','--model',m,'--n','151')
    command('prepare.py','--verify')
    command('report.py')
    write_json(ROOT/'reports/pipeline_complete.json',{'completed':True,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'main_requests':1208,'unique_questions':151,'conditions':4,'models':2,'training':False,'new_heldout':False})

def wait_download():
    dest=ROOT/'models/Qwen3-4B-Instruct-2507'; started=time.monotonic()
    meta=read_json(dest/'repo_api.json')
    weights=[f for f in meta['files'] if f['path'].endswith('.safetensors')]
    required={f['path'] for f in weights}|{'config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','model.safetensors.index.json','generation_config.json'}
    while time.monotonic()-started<3*3600:
        try:
            manifest=read_json(dest/'download_manifest.json')
            if required<={f['file'] for f in manifest['files']} and all((dest/f['path']).stat().st_size==f['size'] for f in weights):
                print('DOWNLOAD COMPLETE: upstream weight hashes recorded',flush=True);return
        except (FileNotFoundError,KeyError,json.JSONDecodeError):pass
        received=0
        for f in weights:
            final=dest/f['path'];part=final.with_suffix(final.suffix+'.partial')
            if final.exists():received+=final.stat().st_size;continue
            size=part.stat().st_size if part.exists() else 0
            folder=dest/'ranges'/f['path']
            size+=sum(p.stat().st_size for p in folder.glob('*') if p.suffix in ('.bin','.partial'))
            received+=min(size,f['size'])
        print('DOWNLOAD PROGRESS',received,'/',sum(f['size'] for f in weights),'bytes',datetime.now(timezone.utc).isoformat(),flush=True)
        time.sleep(55)
    raise TimeoutError('Download still incomplete; preserve ranges and resume without new model calls')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait-for-download',action='store_true');a=p.parse_args()
    if a.wait_for_download:wait_download()
    run()
