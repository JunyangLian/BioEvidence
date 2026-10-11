"""Bounded parallel original-HF ranges; retain prefix and individual resumable chunks."""
import urllib.request
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from fetch_model import DEST, REPO, fetch
from common import *

def run(workers=8, endpoint='https://huggingface.co', request_mib=16):
    assert 1<=workers<=32
    assert endpoint in ('https://huggingface.co','https://hf-mirror.com') and 1<=request_mib<=64
    meta=read_json(DEST/'repo_api.json'); revision=meta['revision']
    plan_path=DEST/'range_download_plan.json'
    if plan_path.exists(): plan=read_json(plan_path)
    else:
        plan=[]
        for f in meta['files']:
            if not f['path'].endswith('.safetensors'):continue
            dest=DEST/f['path']; partial=dest.with_suffix(dest.suffix+'.partial')
            if dest.exists() and dest.stat().st_size==f['size'] and digest(dest)==f['lfs']['oid']:continue
            start=partial.stat().st_size if partial.exists() else 0
            plan.append({'name':f['path'],'size':f['size'],'expected_sha256':f['lfs']['oid'],
                         'prefix_bytes':start,'prefix_sha256':digest(partial) if start else None})
        write_json(plan_path,plan)
    jobs=[]; segment=64*1024*1024
    for f in plan:
        dest=DEST/f['name']
        if dest.exists() and digest(dest)==f['expected_sha256']:continue
        for start in range(f['prefix_bytes'],f['size'],segment):
            jobs.append((f,start,min(start+segment,f['size'])))
    def worker(job):
        f,start,end=job
        folder=DEST/'ranges'/f['name'];folder.mkdir(parents=True,exist_ok=True)
        final=folder/f'{start}-{end}.bin'; part=final.with_suffix('.partial')
        if final.exists():assert final.stat().st_size==end-start;return {'name':f['name'],'start':start,'status':'reused'}
        started=time.perf_counter(); failures=0
        for attempt in range((end-start+request_mib*1024*1024-1)//(request_mib*1024*1024)+2):
            offset=start+(part.stat().st_size if part.exists() else 0)
            if offset==end:break
            req_end=min(end,offset+request_mib*1024*1024)
            try:
                url=f'{endpoint}/{REPO}/resolve/{revision}/{f["name"]}?download=true&v4_range={offset}-{req_end}'
                req=urllib.request.Request(url,headers={'Range':f'bytes={offset}-{req_end-1}'})
                with urllib.request.urlopen(req,timeout=60) as response:
                    assert response.status==206 and response.headers.get('Content-Range')==f'bytes {offset}-{req_end-1}/{f["size"]}',response.headers
                    with part.open('ab') as out:
                        remaining=req_end-offset
                        while remaining:
                            chunk=response.read(min(1024*1024,remaining))
                            if not chunk:raise EOFError(f'Incomplete bounded range {offset}-{end}')
                            out.write(chunk);remaining-=len(chunk)
            except Exception as exc:
                failures+=1
                print('range failure',f['name'],start,type(exc).__name__,str(exc),flush=True)
                if failures==2:raise
        assert part.stat().st_size==end-start
        part.replace(final)
        result={'name':f['name'],'start':start,'end':end,'bytes':end-start,
                'sha256':digest(final),'seconds':time.perf_counter()-started,'status':'ok','transport_endpoint':endpoint,
                'request_mib':request_mib,'note':'Partial prefix may be from earlier official transport; whole upstream SHA is final identity.'}
        write_json(final.with_suffix('.json'),result)
        print('range completed',f['name'],start,end,round(result['seconds'],1),'s',flush=True)
        return result
    results=[];errors=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(worker,j):j for j in jobs}
        for future in as_completed(futures):
            try:results.append(future.result())
            except Exception as exc:errors.append({'job':futures[future],'error':str(exc)})
    write_json(ROOT/'reports/range_download_results.json',{'workers':workers,'transport_endpoint':endpoint,
        'request_mib':request_mib,'results':results,'errors':errors})
    if errors:raise RuntimeError('Bounded ranges failed; preserve all chunks for resume')
    for f in plan:
        dest=DEST/f['name']; partial=dest.with_suffix(dest.suffix+'.partial')
        if dest.exists() and digest(dest)==f['expected_sha256']:continue
        current=partial.stat().st_size if partial.exists() else 0
        assert current>=f['prefix_bytes']
        # An assembly restart is allowed only at a recorded complete segment boundary.
        boundaries=list(range(f['prefix_bytes'],f['size'],segment))+[f['size']]
        assert current in boundaries,'Interrupted assembly must be inspected, not silently overwritten'
        if current==f['prefix_bytes'] and current:assert digest(partial)==f['prefix_sha256']
        with partial.open('ab') as out:
            for start in range(current,f['size'],segment):
                end=min(start+segment,f['size']); chunk=DEST/'ranges'/f['name']/f'{start}-{end}.bin'
                with chunk.open('rb') as inp:
                    for b in iter(lambda:inp.read(8*1024*1024),b''):out.write(b)
        assert partial.stat().st_size==f['size'] and digest(partial)==f['expected_sha256']
        partial.replace(dest)
        print('whole shard SHA verified',f['name'],flush=True)
    fetch(endpoint=endpoint) # Complete assets; verify official Git/LFS content identities.
    manifest=read_json(DEST/'download_manifest.json')
    manifest['transport_provenance']={'initial':'official Hugging Face original files',
        'range_resume':endpoint,'range_report':str(ROOT/'reports/range_download_results.json'),
        'identity':'all three original weight files verified against official API LFS SHA256; mirror changes transport only'}
    write_json(DEST/'download_manifest.json',manifest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8)
    p.add_argument('--endpoint',default='https://huggingface.co');p.add_argument('--request-mib',type=int,default=16)
    a=p.parse_args();run(a.workers,a.endpoint,a.request_mib)
