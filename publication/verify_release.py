"""Verify published bytes and recompute original mechanical scores without GPU."""
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path)
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
 return module

def json_file(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def sha(raw):return hashlib.sha256(raw).hexdigest()

def run():
 manifest=json_file(ROOT/'publication/release_manifest.json')
 for row in manifest['files']:
  p=ROOT/row['path'];assert p.is_relative_to(ROOT)
  data=p.read_bytes();assert len(data)==row['published_bytes'] and sha(data)==row['published_sha256'],row['path']
  original=gzip.decompress(data) if row['encoding']=='gzip' else data
  assert len(original)==row['source_bytes'] and sha(original)==row['source_sha256'],row['path']
 print('Published file hashes and lossless compression verified:',manifest['n_files'])
 parser=load('release_historical_taskb','historical_dependencies/BioEvidence-v1/src/bioevidence/inference/prompts_taskb.py')
 scorer=load('release_historical_score','historical_dependencies/BioEvidence-v2/scripts/v2_stageb_dev_analysis.py')
 checked=0
 for version,models in [(4,['base_06b','instruct_4b']),(5,['base_06b','e7_06b','instruct_4b','tuned_4b'])]:
  for model in models:
   root=ROOT/f'BioEvidence-v{version}/runs/{model}/dev151'
   rows=lines(root/'predictions.jsonl');expected=json_file(root/'analysis.json')
   assert len(rows)==604 and len({(r['question_id'],r['condition']) for r in rows})==604
   for row in rows:
    parsed=parser.parse_output(row['raw_output'],n_evidence=len(row['chunk_order'])).to_dict()
    for key in ['status','label','reason','answerable','citations','parse_note','citation_issues']:
     stored=row.get('parsed_status',row['status']) if key=='status' else row[key]
     assert parsed[key]==stored,(version,model,row['question_id'],row['condition'],key)
    assert len(row['input_token_ids'])==row['input_tokens']
    assert set(row['display_to_chunk'].values())==set(row['chunk_order'])
    checked+=1
   for condition,reference in expected['per_condition'].items():
    subset=[r for r in rows if r['condition']==condition];assert len(subset)==151
    actual=scorer.metrics([(r['gold'],r['label'],r['status']) for r in subset])
    assert actual==reference['classification'],(version,model,condition)
   print('Original parser and per-condition classification verified:',version,model,len(rows))
 reference=json_file(ROOT/'historical_dependencies/BioEvidence-v2/runs/P1-v2-stageB-order-20260924/stageb_dev_analysis.json')['main_denominator_151']
 e7=lines(ROOT/'BioEvidence-v5/runs/e7_06b/dev151/predictions.jsonl')
 for condition,expected in reference.items():
  assert scorer.metrics([(r['gold'],r['label'],r['status']) for r in e7 if r['condition']==condition])==expected
 final=json_file(ROOT/'BioEvidence-v5/reports/development_comparison.json')
 assert final['cost']['comparison_rows']==2416 and final['cost']['new_unique_generation_requests']==604
 assert final['integrity']['passed'] and json_file(ROOT/'BioEvidence-v5/reports/historical_protection.json')['passed']
 print('PASS:',checked,'stored records checked (V4/V5 include reused records); V5 matrix=2416, new requests=604')
 print('This verifies published bytes, frozen parser and original classification formulas. It does not regenerate models, rerun harness or independently validate semantic/human references.')

if __name__=='__main__':run()
