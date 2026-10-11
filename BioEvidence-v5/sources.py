"""Seal source identity and verify historical files without writing to them."""
from datetime import datetime,timezone
from common import *
def inventory():
    dest=ROOT/'source_inventory.json';assert not dest.exists(),'Immutable inventory already exists'
    files=read_json(V4/'source_inventory.json')['files'].copy()
    # Protect all meaningful V4 sources, data, runs, reports and original model assets.
    # Runtime caches, downloaded range duplicates, pip wheelhouse and .venv have separate identities.
    excluded={'.venv','cache','tmp','wheelhouse','ranges'}
    pending=[V4]
    while pending:
        folder=pending.pop()
        for p in folder.iterdir():
            if p.is_dir():
                if p.name not in excluded:pending.append(p)
            elif p.is_file():
                st=p.stat();files[p.relative_to(PROJECT).as_posix()]={'path':str(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest(p)}
    baseline=read_json(V4/'reports/historical_protection.json');assert baseline['passed']
    write_json(dest,{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'files':files,
        'v4_excluded_categories':sorted(excluded),'v4_runtime_identity':'environment.json + dependency locks + package install archives; never imported as site-packages',
        'scope':'All V1-V3 original 1411-file baseline; V4 sources/data/results/reports and original model assets, excluding runtime/cache duplicates',
        'applicable_agents':[]})
    dest.chmod(0o444);print('Read-only source baseline',len(files),'files',flush=True)
def verify():
    inv=read_json(ROOT/'source_inventory.json');changed=[];mtime=[]
    for k,r in inv['files'].items():
        p=Path(r['path'])
        if not p.exists() or digest(p)!=r['sha256']:changed.append(k)
        if p.exists() and p.stat().st_mtime_ns!=r['mtime_ns']:mtime.append(k)
    original={p.relative_to(PROJECT).as_posix() for v in (V1,V2,V3) for p in v.rglob('*') if p.is_file()}
    additions=sorted(original-{k for k in inv['files'] if not k.startswith('BioEvidence-v4/')})
    v4_files=set();pending=[V4];excluded=set(inv['v4_excluded_categories'])
    while pending:
        folder=pending.pop()
        for p in folder.iterdir():
            if p.is_dir():
                if p.name not in excluded:pending.append(p)
            elif p.is_file():v4_files.add(p.relative_to(PROJECT).as_posix())
    v4_additions=sorted(v4_files-{k for k in inv['files'] if k.startswith('BioEvidence-v4/')})
    result={'passed':not changed and not mtime and not additions and not v4_additions,'n_hashed':len(inv['files']),
        'changed_or_missing':changed,'mtime_changed':mtime,'v1_v3_additions':additions,
        'v4_meaningful_file_additions':v4_additions,'v4_excluded_categories':sorted(excluded),
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'v4_scope':inv['scope']}
    write_json(ROOT/'reports/historical_protection.json',result);assert result['passed'],result
    print('Historical source protection passed',len(inv['files']),flush=True)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();verify() if a.verify else inventory()
