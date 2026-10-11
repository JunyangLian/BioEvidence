"""Inventory and export actual sealed dev151 evidence; no retrieval rerun."""
import argparse
import csv
from datetime import datetime, timezone
from common import *

def snapshot():
    dest = ROOT / 'source_inventory.json'
    if dest.exists():
        raise RuntimeError('Immutable inventory exists; use --verify')
    files, missing = {}, []
    # Hash every historical file, including frozen predictions and weights.
    for version in (V1, V2, V3):
        for p in sorted(version.rglob('*')):
            if p.is_file():
                st = p.stat()
                files[p.relative_to(PROJECT).as_posix()] = {'path': str(p), 'bytes': st.st_size,
                    'mtime_ns': st.st_mtime_ns, 'sha256': digest(p)}
    required = [V1/'configs/eval.yaml', V1/'configs/train_taskb.yaml',
        V1/'data/manifests/split_pubmedqa_pqal_v1.jsonl', STAGEB/'order_plan_all_samples.json',
        STAGEB/'predictions_order_dev.jsonl', V1/'artifacts/adapters/p6-taskb-lora/adapter_model.safetensors']
    for p in required:
        if not p.exists(): missing.append(str(p))
    frozen = read_json(V1/'runs/P10-test-final-20260922/frozen_config_manifest.json')
    checks = {k: files['BioEvidence-v1/'+k]['sha256'] == v['sha256'] for k,v in frozen['files'].items()}
    write_json(dest, {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'historical_access': 'read-only; no pycache writes; all additions confined to v4',
        'applicable_agents': [], 'missing': missing, 'files': files,
        'v1_frozen_manifest_checks': checks, 'v1_freeze_ok': all(checks.values()),
        'model_4b': 'not present in BioEvidence at inventory time',
        'notes': ['v1 A1 soft section reorder; semantic reranking B1/B2',
                  'E7 p6-taskb-lora differs from v2 C1 old-target adapter',
                  'v1 accuracy excludes generic failure; eval_taskb maps failures to invalid',
                  'v2 Stage B all rows denominator; citation diagnostics cited-row denominator',
                  'v3 uses its own classification/dev26 definitions; not silently unified']})
    dest.chmod(0o444)
    print('Inventory:', len(files), 'historical hashes;', len(checks), 'v1 frozen checks', flush=True)

def verify():
    inv = read_json(ROOT/'source_inventory.json')
    current = {p.relative_to(PROJECT).as_posix():p for v in (V1,V2,V3) for p in v.rglob('*') if p.is_file()}
    changed = []
    mtime_changed = []
    for key, rec in inv['files'].items():
        p = current.get(key)
        if p is None or digest(p) != rec['sha256']:
            changed.append(key)
        if p is not None and p.stat().st_mtime_ns != rec['mtime_ns']:
            mtime_changed.append(key)
    new = sorted(set(current)-set(inv['files']))
    report = {'n_hashed': len(inv['files']), 'changed_or_missing': changed,
              'unexpected_additions': new, 'last_write_time_changed':mtime_changed,
              'passed': not changed and not new and not mtime_changed,
              'generated_at_utc': datetime.now(timezone.utc).isoformat()}
    write_json(ROOT/'reports/historical_protection.json', report)
    print(report, flush=True)
    assert report['passed']

def export():
    from bioevidence.retrieval.section_aware import is_result_section
    plans = read_json(STAGEB/'order_plan_all_samples.json')['plans']
    proc = V1/'data/processed/pubmedqa'
    chunks = {r['chunk_id']:r for r in jsonl(proc/'corpus_chunks.jsonl')}
    questions = {r['question_id']:r for r in jsonl(proc/'questions.jsonl')}
    gold = {r['question_id']:r['gold_label'] for r in jsonl(proc/'gold_labels.jsonl')}
    manifest = jsonl(V1/'data/manifests/split_pubmedqa_pqal_v1.jsonl')
    dev = {r['question_id'] for r in manifest if r['scheme']=='internal_70_30' and r['split']=='dev'}
    test = {r['question_id'] for r in manifest if r['scheme']=='official' and r['split']=='test'}
    assert len(dev) == 151 and {p['question_id'] for p in plans} == dev and not dev & test
    frozen = {r['question_id']:r for r in jsonl(V1/'runs/P7-retrieval-20260921/predictions_e7_taskb_A2_quota.jsonl')}
    v3blocks = {r['question_id']:r['evidence_block'] for r in jsonl(V3/'cache/evidence/v3_dev151_b0_evidence.jsonl')}
    rows = []
    for p in plans:
        qid = p['question_id']
        assert p['sealed_chunk_ids'] == frozen[qid]['evidence_meta']['used_chunk_ids']
        actual_orders = order.build_orders(p['sealed_chunk_ids'],
            lambda cid: is_result_section(chunks[cid]['section']), f'v2-order-20260924|{qid}')
        for cond, cp in p['conditions'].items():
            assert actual_orders[cond] == cp['order']
            assert set(cp['order']) == set(p['sealed_chunk_ids'])
            block = order.render_block(cp['order'], chunks)
            assert order.sha8(block) == cp['block_sha8']
            if cond == 'B0_original': assert block == v3blocks[qid]
            rows.append({'sample_id':'D'+qid, 'question_id':qid, 'condition':cond,
                'source_split':'internal_70_30/dev', 'question':questions[qid]['question'],
                'gold':gold[qid], 'reference_source':str(proc/'gold_labels.jsonl'),
                'gold_answerable_proxy':frozen[qid]['gold_answerable'],
                'chunk_order':cp['order'], 'display_to_chunk':cp['display_to_chunk'],
                'evidence': [chunks[cid] for cid in cp['order']], 'evidence_block':block,
                'block_sha8':cp['block_sha8'], 'identical_to_baseline':cp['identical_to_baseline'],
                'result_positions':cp['result_positions'], 'messages':tb.build_messages(questions[qid]['question'],block),
                'template_fingerprint':tb.template_fingerprint(), 'source_plan':str(STAGEB/'order_plan_all_samples.json'),
                'evidence_budget_v1':900, 'block_token_len_v2':cp['block_token_len']})
    write_jsonl(ROOT/'data/dev151_conditions.jsonl', rows)
    unified = {r['anonymous_id']:r for r in csv.DictReader((V2/'data/review/annotations_all30_unified.csv').open(encoding='utf-8-sig'))}
    bm = read_json(V2/'data/review/c2_smoke/backend_mapping.json')['mapping']
    refs = []
    for r in bm:
        u = unified[r['source_anon']]
        expected=[e['chunk_id'] for e in r['evidence']]
        actual=next(p['sealed_chunk_ids'] for p in plans if p['question_id']==r['question_id'])
        assert expected==actual,(r['question_id'],'human reference evidence mismatch')
        refs.append({'question_id':r['question_id'], 'source_anon':r['source_anon'],
                     'evidence_sufficiency':u['evidence_sufficiency'], 'retrieval_condition':u['retrieval_condition'],
                     'verified_B0_chunk_ids':expected,'evidence_identity_verified':True,
                     'provenance':'historical human-returned v2 unified; reviewer/time unknown; repeated dev subset'})
    assert len(refs)==26
    assert sum(r['evidence_sufficiency']=='不足' for r in refs)==14
    assert sum(r['evidence_sufficiency']=='充分' for r in refs)==12
    write_json(ROOT/'data/human_dev26_reference.json',refs)
    write_json(ROOT/'reports/assembly.json',{'passed':True,'samples':151,'conditions':4,'rows':len(rows),
        'B0_frozen_used_ids_exact':151,'B0_v3_block_exact':151,'all_plan_hashes_exact':604,
        'permutation_matches_historical_rules':604,'no_new_retrieval_or_truncation':True,
        'input_changed_pairs':sum(not r['identical_to_baseline'] for r in rows),
        'intervention':'order plus renumbering; repeatedly used development data'})
    print('Export verified:',len(rows),'actual dev inputs',flush=True)

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--verify',action='store_true'); ap.add_argument('--export',action='store_true'); a=ap.parse_args()
    if a.verify: verify()
    elif a.export: export()
    else: snapshot(); export()
