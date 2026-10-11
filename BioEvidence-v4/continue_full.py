"""Resume the interrupted 4B full run, preserving prior logs and base results."""
import subprocess
from datetime import datetime, timezone
from common import *
from run_remaining import event, command

def run():
    done=ROOT/'reports/pipeline_complete.json'
    if done.exists():
        print('Pipeline already completed; no model calls'); return
    base=read_json(ROOT/'runs/base_06b/dev151/summary.json')
    assert base['n']==604 and base['input_system_and_context_checks_passed']
    assert base['config_fingerprint']==read_json(ROOT/'runs/base_06b/smoke10/summary.json')['config_fingerprint']
    model='instruct_4b'; smoke=read_json(ROOT/f'runs/{model}/smoke10/summary.json')
    caches=list((ROOT/'cache/generation'/model/smoke['config_fingerprint']).glob('*.json'))
    completed=sum(read_json(p)['finish_reason']!='exception' for p in caches)
    event('RESUME',{'model':model,'completed_cache_entries':completed,'remaining_requests':604-completed,
        'projected_remaining_generation_seconds':(604-completed)*read_json(ROOT/'reports/expansion_cost_plan.json')['models'][model]['measured_mean_seconds'],
        'locked_config_fingerprint':smoke['config_fingerprint']})
    log=ROOT/'logs/generate_model_instruct_4b_n_151.log'
    event('START',['generate.py','--model',model,'--n','151','resume'])
    with log.open('a',encoding='utf-8') as out:
        out.write('\nRESUME '+datetime.now(timezone.utc).isoformat()+'\n');out.flush()
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'generate.py'),'--model',model,'--n','151'],
            stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,f'Resumed model run failed: {log}'
    event('DONE',['generate.py','--model',model,'--n','151','resume'])
    command('prepare.py','--verify')
    command('report.py')
    write_json(done,{'completed':True,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'main_requests':1208,'unique_questions':151,'conditions':4,'models':2,'training':False,'new_heldout':False})

if __name__=='__main__':run()
