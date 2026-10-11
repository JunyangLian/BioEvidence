"""Read-only historical imports and v4-only artifact helpers."""
import sys
sys.dont_write_bytecode = True
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
V1, V2, V3 = [PROJECT / f'BioEvidence-v{i}' for i in (1, 2, 3)]
STAGEB = V2 / 'runs/P1-v2-stageB-order-20260924'
for key, val in {'HF_HOME': 'cache/hf', 'HF_DATASETS_CACHE': 'cache/datasets',
                 'LM_HARNESS_CACHE_PATH': 'cache/harness', 'TMP': 'tmp', 'TEMP': 'tmp',
                 'PIP_CACHE_DIR': 'cache/pip', 'MPLCONFIGDIR': 'cache/mpl'}.items():
    os.environ[key] = str(ROOT / val)
    (ROOT / val).mkdir(parents=True, exist_ok=True)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(V1 / 'src'))

def historical(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

from bioevidence.inference import prompts_taskb as tb
from bioevidence.evaluation.metrics import ItemResult, compute_metrics
order = historical('v4_history_order', V2 / 'scripts/v2_stageb_order_control.py')
v2score = historical('v4_history_score', V2 / 'scripts/v2_stageb_dev_analysis.py')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding='utf-8-sig').splitlines() if l.strip()]

def write_json(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'v4-only write guard: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def write_jsonl(path, rows):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('v4-only write guard')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, default=str) + '\n' for r in rows), encoding='utf-8')

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

def classification(rows, policy='v2'):
    if not rows:
        return {'n': 0, 'n_correct': 0, 'accuracy': None, 'macro_f1': None,
                'zero_denominator': 'N/A; historical v2 function requires nonempty input'}
    triples = [(r['gold'], r.get('label'), r['status']) for r in rows]
    if policy == 'v2':
        return v2score.metrics(triples)
    return compute_metrics([ItemResult(r['question_id'], r['gold'],
        'ok' if r['status'] == 'ok' else 'invalid',
        r.get('label') if r['status'] == 'ok' else None) for r in rows]).to_dict()
