"""Delivery verification after real runs and sealed-source checks."""
from common import *
from datetime import datetime,timezone

def run():
    protection=read_json(ROOT/'reports/historical_protection.json');assert protection['passed']
    result=read_json(ROOT/'reports/development_comparison.json')
    assert result['cost']['comparison_rows']==2416 and result['integrity']['passed']
    assert result['cost']['new_unique_generation_requests']==604
    train=read_json(ROOT/'runs/training/full/report.json');assert train['global_step']==219
    ai=read_json(ROOT/'ai_assisted/summary.json');assert ai['n_opinions']==16 and ai['n_questions']==2
    lock=read_json(ROOT/'ai_assisted/audit_lock.json');assert lock['before_joining_model_map'] and not lock['human_truth']
    for name,sha in lock['hashes'].items():assert digest(ROOT/'ai_assisted'/name)==sha,('AI locked file changed',name)
    final_adapter=Path(train['adapter_dir'])
    for name,sha in train['adapter_hashes'].items():assert digest(final_adapter/name)==sha,('Final adapter changed',name)
    env=read_json(ROOT/'environment.json')
    upstream=read_json(V4/'reports/source_commits.json')
    installed={r['metadata']['name'].replace('-','_').lower():r['download_info']['archive_info']['hashes']['sha256']
        for r in read_json(ROOT/'install-baseline-report.json')['install']}
    for name,r in upstream.items():
        assert installed[name]==r['wheel_sha256'],('Source commit archive mismatch',name)
        r['V5_archive_match_verified']=True
        r['read_only_reference']=str(V4/'reports/source_commits.json')
    upstream['TRL']={'source_commit':None,'version':'1.13.0',
        'boundary':'No independently verified Git commit; official PyPI wheel SHA256 and installed trainer source SHA256 locked instead',
        'install_report_sha256':digest(ROOT/'install-trl-report.json')}
    write_json(ROOT/'reports/source_commits.json',upstream)
    env['source_commits']=upstream
    for name,row in env['runner_forks'].items():
        row['v5_sha256']=digest(ROOT/name)
    env['final_v5_source_hashes']={p.name:digest(p) for p in ROOT.glob('*.py')}
    env['final_fork_changes']='Adds tuned4B and condition scope; fingerprints native .jinja, common/parser/scorer source; atomic V5 JSON cache writes. Analysis explicitly separates historical costs and missing telemetry; classification remains frozen.'
    write_json(ROOT/'environment.json',env)
    artifacts={}
    for folder in ['config','data','reports','runs','ai_assisted']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ['checkpoints','smoke_adapter']) and p.name!='delivery_manifest.json':
                artifacts[p.relative_to(ROOT).as_posix()]={'bytes':p.stat().st_size,'sha256':digest(p)}
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in ['.py','.txt','.json','.md'] and p.name!='V5_STATUS.md':
            artifacts[p.name]={'bytes':p.stat().st_size,'sha256':digest(p)}
    for p in final_adapter.iterdir():
        if p.is_file():artifacts[p.relative_to(ROOT).as_posix()]={'bytes':p.stat().st_size,'sha256':digest(p)}
    write_json(ROOT/'reports/delivery_manifest.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'passed':True,'files':artifacts,'n_files':len(artifacts),
        'scope':'V5 source/config/data/reports/final runs/AI-assisted records; intermediate checkpoints/smoke adapter excluded; final adapter identity in training report',
        'sealed_source_protection':protection,'limitations':result['limits']})
    for name,r in artifacts.items():assert digest(ROOT/name)==r['sha256']
    print('V5 delivery verified',len(artifacts),'files',flush=True)
if __name__=='__main__':run()
