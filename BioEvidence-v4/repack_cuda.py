"""Build a v4-only installation wheel from the verified local CUDA distribution.

This is a RECORD-checked local snapshot, not a newly downloaded upstream wheel.
No symlinks or shared site-packages are used by the v4 environment.
Run using the existing environment's interpreter, with -B.
"""
import base64
import csv
import hashlib
import importlib.metadata as md
import io
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
def run():
    dist=md.distribution('torch')
    assert dist.version=='2.14.0+cu130',dist.version
    wheel_dir=ROOT/'wheelhouse'; wheel_dir.mkdir(exist_ok=True)
    wheel=wheel_dir/'torch-2.14.0+cu130-cp313-cp313-win_amd64.whl'
    rows=[]; mismatches=[]; skipped=[]
    with zipfile.ZipFile(wheel,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as out:
        for file in dist.files:
            name=str(file).replace('\\','/')
            if '..' in Path(name).parts or name.endswith('/RECORD'):
                skipped.append(name); continue
            src=Path(dist.locate_file(file))
            if not src.is_file(): continue
            h=hashlib.sha256()
            with src.open('rb') as inp, out.open(name,'w',force_zip64=True) as dst:
                for block in iter(lambda:inp.read(8*1024*1024),b''):
                    dst.write(block); h.update(block)
            encoded=base64.urlsafe_b64encode(h.digest()).rstrip(b'=').decode()
            if file.hash and file.hash.mode=='sha256' and file.hash.value!=encoded:
                mismatches.append(name)
            rows.append((name,'sha256='+encoded,str(src.stat().st_size)))
        record=f'torch-{dist.version}.dist-info/RECORD'
        rows.append((record,'',''))
        text=io.StringIO(); csv.writer(text,lineterminator='\n').writerows(rows)
        out.writestr(record,text.getvalue())
    assert not mismatches,mismatches
    h=hashlib.sha256()
    with wheel.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    report={'package':'torch','version':dist.version,'source_distribution':str(dist.locate_file('')),
            'wheel':str(wheel),'sha256':h.hexdigest(),'bytes':wheel.stat().st_size,
            'record_verified_files':len(rows)-1,'record_hash_mismatches':mismatches,
            'excluded_outside_package_scripts':skipped,'install_method':'independent local wheel; no shared environment links',
            'origin_note':'Local repack of previously verified CUDA install; not the upstream wheel archive'}
    (ROOT/'cuda_snapshot.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':run()
