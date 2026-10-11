"""Install an independent V5 runtime using locked V4 archives and pinned TRL."""
import subprocess
import shutil
from common import *
def run():
    os.environ['PIP_CONFIG_FILE']='NUL'
    py=ROOT/'.venv/Scripts/python.exe'
    if not py.exists():
        result=subprocess.run([sys.executable,'-B','-m','venv',str(ROOT/'.venv')]);assert result.returncode==0
    probe=subprocess.run([str(py),'-B','-c','import pip'],capture_output=True)
    if probe.returncode:
        result=subprocess.run([str(py),'-B','-m','ensurepip','--upgrade','--default-pip']);assert result.returncode==0
    lock=V4/'requirements-hashed.txt'
    (ROOT/'requirements-v4-baseline-hashed.txt').write_bytes(lock.read_bytes())
    commands=[['-m','pip','install','--require-hashes','--find-links',str(V4/'wheelhouse'),'-r',str(ROOT/'requirements-v4-baseline-hashed.txt'),
        '--index-url','https://pypi.org/simple','--report',str(ROOT/'install-baseline-report.json')],
        ['-m','pip','install','trl==1.13.0','-c',str(ROOT/'constraints-baseline.txt'),'--index-url','https://pypi.org/simple',
         '--report',str(ROOT/'install-trl-report.json')]]
    baseline=read_json(V4/'install-snapshot-report.json')
    (ROOT/'constraints-baseline.txt').write_text('\n'.join(f"{r['metadata']['name']}=={r['metadata']['version']}" for r in baseline['install'])+'\n',encoding='utf-8')
    for index,args in enumerate(commands):
        log=ROOT/f'logs/install_{index}.log';log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('w',encoding='utf-8') as out:
            result=subprocess.run([str(py),'-X','utf8','-B',*args],stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,f'Install failed: {log}'
        print('Installed stage',index,flush=True)
    print('Independent V5 baseline and TRL installed',flush=True)
if __name__=='__main__':run()
