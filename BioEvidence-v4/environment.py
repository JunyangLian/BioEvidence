"""Save actual isolated runtime, source hashes, and installed dependency lock."""
import importlib.metadata as md
import platform
import subprocess
from datetime import datetime,timezone
from common import *

def run():
    import torch
    import bitsandbytes as bnb
    import lm_eval
    assert Path(sys.prefix).resolve()==(ROOT/'.venv').resolve(),'Must run inside v4 independent env'
    assert torch.cuda.is_available()
    p=subprocess.run([sys.executable,'-X','utf8','-B','-m','pip','freeze','--all'],capture_output=True,text=True,encoding='utf-8')
    assert p.returncode==0,p.stderr
    (ROOT/'requirements-lock.txt').write_text(p.stdout,encoding='utf-8')
    install=read_json(ROOT/'install-snapshot-report.json')
    locked=[]
    for e in install['install']:
        package=e['metadata']['name'];version=e['metadata']['version']
        sha=e['download_info']['archive_info']['hashes']['sha256']
        locked.append(f'{package}=={version} --hash=sha256:{sha}')
    (ROOT/'requirements-hashed.txt').write_text('\n'.join(sorted(locked))+'\n',encoding='utf-8')
    versions={d.metadata['Name']:d.version for d in md.distributions()}
    layer=bnb.nn.Linear4bit(64,64,bias=False,compute_dtype=torch.bfloat16,quant_type='nf4').to('cuda')
    with torch.no_grad():res=layer(torch.randn(2,64,device='cuda',dtype=torch.bfloat16))
    smi=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used,memory.free,compute_cap',
        '--format=csv'],capture_output=True,text=True)
    harness=Path(lm_eval.__file__).parent
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'python_executable':sys.executable,
        'python_version':sys.version,'prefix':sys.prefix,'base_prefix':sys.base_prefix,'os':platform.platform(),
        'packages':versions,'torch_cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),
        'gpu':smi.stdout,'capability':torch.cuda.get_device_capability(),
        'bitsandbytes_forward':{'shape':list(res.shape),'dtype':str(res.dtype),'passed':True},
        'harness_source_path':str(harness),'source_hashes':{f:digest(harness/f) for f in
            ['api/task.py','api/model.py','models/huggingface.py','evaluator.py']},
        'official_documentation_reviewed':[
            'https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md',
            'https://huggingface.co/docs/transformers/quantization/bitsandbytes',
            'https://huggingface.co/docs/bitsandbytes/installation',
            'https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507'],
        'cuda_install':'v4 independent RECORD-verified repack wheel; see cuda_snapshot.json',
        'isolation':{'system_site_packages':False,'torch_location':str(Path(torch.__file__).resolve()),
                     'historical_paths_on_pythonpath':'v1 source only, read-only, pycache disabled'}}
    write_json(ROOT/'environment.json',report)
    check=subprocess.run([sys.executable,'-X','utf8','-B','-m','pip','check'],capture_output=True,text=True,encoding='utf-8')
    write_json(ROOT/'reports/pip_check.json',{'exit_code':check.returncode,'stdout':check.stdout,'stderr':check.stderr})
    assert check.returncode==0,check.stdout
    print('Independent env verified:',torch.__version__,md.version('lm_eval'),md.version('transformers'),flush=True)

if __name__=='__main__':run()
