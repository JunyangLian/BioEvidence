"""Advance the approved fixed protocol; gates are integrity/resources, never scores."""
from common import *
import subprocess,time,argparse,ctypes,traceback

def command(script,*args):
    target=ROOT/script;log=ROOT/'logs'/('pipeline_'+script.replace('.py','')+'_'+'_'.join(args).replace('--','')+'.log')
    print('RUN',script,*args,flush=True)
    with log.open('w',encoding='utf-8') as f:
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(target),*args],cwd=PROJECT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError(f'{script} failed ({p.returncode}); see {log}')

def run(pid):
    if pid:
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p;kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x1000,False,pid);assert handle,'Cannot wait for authorized trainer PID'
        started=time.monotonic()
        while True:
            code=ctypes.c_ulong();assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
            if code.value!=259:break
            assert time.monotonic()-started<21600,'Training wait exceeded registered resource budget'
            time.sleep(5)
        kernel.CloseHandle(handle);assert code.value==0,('Trainer failed',code.value)
    assert read_json(ROOT/'runs/training/full/report.json')['passed']
    assert read_json(ROOT/'reports/reuse_integrity.json')['passed']
    command('alignment.py')
    command('generate.py','--model','tuned_4b','--n','10','--b0-only')
    command('integrity.py','--scope','smoke10','--only-tuned')
    smoke=read_json(ROOT/'runs/tuned_4b/smoke10/summary.json')
    assert smoke['generation_exceptions']==0,'Model failure is a technical gate; preserve real failures'
    measured=smoke['elapsed_seconds'];estimated=measured/10*604
    write_json(ROOT/'reports/expansion_cost_preflight.json',{'expected_unique_new_requests':604,
        'smoke_requests_already_in_cache':10,'B0_remaining':141,'other_order_requests':453,
        'smoke_elapsed_seconds_including_load':measured,'conservative_estimated_total_seconds':estimated,
        'declared_budget_seconds':7200,'score_based_gate':False})
    assert estimated<7200,'Generation wall estimate exceeds declared budget'
    command('generate.py','--model','tuned_4b','--n','151','--b0-only')
    command('integrity.py','--scope','B0_dev151')
    command('report.py','--b0-only')
    command('generate.py','--model','tuned_4b','--n','151')
    command('integrity.py')
    command('ai_join.py')
    command('report.py')
    command('sources.py','--verify')
    command('finalize.py')
    write_json(ROOT/'reports/pipeline_complete.json',{'passed':True,'training':'fixed final3epochs',
        'unique_comparison_rows':2416,'reused_rows':1812,'new_generation_rows':604})
    print('V5 APPROVED PROTOCOL COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--train-pid',type=int,default=0);a=p.parse_args()
    try:run(a.train_pid)
    except Exception:
        err=traceback.format_exc();write_json(ROOT/f'reports/pipeline_failure_{int(time.time())}.json',{'error':err});print(err,flush=True);raise
