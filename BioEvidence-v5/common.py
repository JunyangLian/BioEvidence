"""V5-only writes and cache roots; sealed BioEvidence sources are read-only."""
import sys
sys.dont_write_bytecode=True
import os
import json
import hashlib
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
V1,V2,V3,V4=[PROJECT/f'BioEvidence-v{i}' for i in range(1,5)]
STAGEB=V2/'runs/P1-v2-stageB-order-20260924'
for k,v in {'HF_HOME':'cache/hf','HF_DATASETS_CACHE':'cache/datasets','LM_HARNESS_CACHE_PATH':'cache/harness',
    'TMP':'tmp','TEMP':'tmp','PIP_CACHE_DIR':'cache/pip','MPLCONFIGDIR':'cache/mpl','TORCHINDUCTOR_CACHE_DIR':'cache/torchinductor',
    'TRITON_CACHE_DIR':'cache/triton'}.items():
    os.environ[k]=str(ROOT/v);(ROOT/v).mkdir(parents=True,exist_ok=True)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(V1/'src'))
def historical(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
from bioevidence.inference import prompts_taskb as tb
from bioevidence.evaluation.metrics import ItemResult,compute_metrics
order=historical('v5_order',V2/'scripts/v2_stageb_order_control.py')
v2score=historical('v5_score',V2/'scripts/v2_stageb_dev_analysis.py')
def read_json(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def jsonl(p):return [json.loads(l) for l in Path(p).read_text(encoding='utf-8-sig').splitlines() if l.strip()]
def write_json(p,v):
    p=Path(p).resolve();assert p.is_relative_to(ROOT),p;p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_name(p.name+f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    os.replace(temp,p)
def write_jsonl(p,rs):
    p=Path(p).resolve();assert p.is_relative_to(ROOT),p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(r,ensure_ascii=False,default=str)+'\n' for r in rs),encoding='utf-8')
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def fingerprint(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
def classification(rs,policy='v2'):
    if not rs:return {'n':0,'n_correct':0,'accuracy':None,'macro_f1':None,'zero_denominator':'N/A; frozen v2 requires nonempty'}
    if policy=='v2':return v2score.metrics([(r['gold'],r.get('label'),r['status']) for r in rs])
    return compute_metrics([ItemResult(r['question_id'],r['gold'],'ok' if r['status']=='ok' else 'invalid',r.get('label') if r['status']=='ok' else None) for r in rs]).to_dict()
