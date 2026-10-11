"""Resume official HF original safetensors only; preserve metadata/hashes."""
import urllib.request
import time
import argparse
from common import *

REPO='Qwen/Qwen3-4B-Instruct-2507'
DEST=ROOT/'models/Qwen3-4B-Instruct-2507'
def fetch(only=None,endpoint='https://huggingface.co'):
    assert endpoint in ('https://huggingface.co','https://hf-mirror.com')
    DEST.mkdir(parents=True,exist_ok=True)
    api=f'https://huggingface.co/api/models/{REPO}/tree/main?recursive=true&expand=false'
    if (DEST/'repo_api.json').exists():
        meta=read_json(DEST/'repo_api.json');revision=meta['revision'];tree=meta['files']
    else:
        with urllib.request.urlopen(api,timeout=30) as r: tree=json.load(r)
        info_url=f'https://huggingface.co/api/models/{REPO}'
        with urllib.request.urlopen(info_url,timeout=30) as r: info=json.load(r)
        revision=info['sha']
        write_json(DEST/'hf_model_info.json',info)
        meta={'revision':revision,'files':tree}
        write_json(DEST/'repo_api.json',meta)
    files=[{'Type':'blob','Path':f['path'],'Size':f.get('size',0),'Sha256':f.get('lfs',{}).get('oid'),
            'GitBlob':f['oid'] if not f.get('lfs') else None} for f in tree if f['type']=='file']
    chosen=[f for f in files if f['Type']=='blob' and (f['Path'].endswith('.safetensors') or f['Path'] in
        ['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','merges.txt','vocab.json',
         'model.safetensors.index.json','LICENSE','README.md'])]
    if only:chosen=[f for f in chosen if f['Path']==only]
    assert chosen,'No matching model file'
    manifest=DEST/(f'download_manifest_{only}.json' if only else 'download_manifest.json')
    logs=[]
    for f in chosen:
        name=f['Path']; p=DEST/name; part=p.with_suffix(p.suffix+'.partial')
        expected=f.get('Sha256') or f.get('SHA256')
        size=f.get('Size',0)
        def git_matches(file):
            return not f['GitBlob'] or hashlib.sha1(f'blob {size}\0'.encode()+file.read_bytes()).hexdigest()==f['GitBlob']
        if p.exists() and p.stat().st_size == size and (not expected or digest(p)==expected) and git_matches(p):
            logs.append({'file':name,'bytes':size,'sha256':digest(p),'expected_sha256':expected,
                         'expected_git_blob':f['GitBlob'],'status':'reused'}); continue
        url=f'{endpoint}/{REPO}/resolve/{revision}/{name}?download=true'
        # Large streaming responses ended early in this network. Fetch bounded
        # byte ranges instead, with a finite retry bound and fresh query per offset.
        segment=64*1024*1024
        last_failed_offset=None
        for attempt in range((size+segment-1)//segment+10):
            try:
                offset=part.stat().st_size if part.exists() else 0
                if offset==size: break
                print('request',name,'offset',offset,'attempt',attempt+1,flush=True)
                end=min(size-1,offset+segment-1)
                req=urllib.request.Request(url+f'&v4_offset={offset}',headers={'Range':f'bytes={offset}-{end}'})
                with urllib.request.urlopen(req,timeout=60) as r:
                    resume=r.status==206 and offset>0
                    print('response',r.status,'length',r.headers.get('Content-Length'),'range',r.headers.get('Content-Range'),flush=True)
                    if offset:
                        assert resume and r.headers.get('Content-Range','').startswith(f'bytes {offset}-'), 'Resume not honored; preserve partial rather than overwrite'
                    with part.open('ab' if resume else 'wb') as out:
                        progress=offset
                        remaining=end-offset+1
                        while True:
                            chunk=r.read(min(1024*1024,remaining))
                            if not chunk: break
                            out.write(chunk)
                            remaining-=len(chunk)
                            if out.tell()-progress>=128*1024*1024:
                                progress=out.tell(); print(name,'received',progress,'/',size,flush=True)
                            if remaining==0:break
                new_size=part.stat().st_size
                assert new_size>offset,(name,'no progress',offset)
                print(name,'checkpoint',new_size,'/',size,flush=True)
                if new_size==size:break
            except Exception as exc:
                print(name,'attempt',attempt+1,type(exc).__name__,str(exc),flush=True)
                # At most two failures at an unchanged byte offset.
                fail_offset=part.stat().st_size if part.exists() else 0
                if last_failed_offset==fail_offset: raise
                last_failed_offset=fail_offset
        assert part.stat().st_size==size,(name,part.stat().st_size,size)
        actual=digest(part)
        assert not expected or expected==actual,(name,'remote sha mismatch')
        assert git_matches(part),(name,'official Git blob mismatch')
        part.replace(p)
        logs.append({'file':name,'bytes':size,'sha256':actual,'expected_sha256':expected,
                     'expected_git_blob':f['GitBlob'],'status':'ok','url':url})
        write_json(manifest,{'repo':REPO,'revision':revision,'api':api,'files':logs})
        print(name,size,'verified',flush=True)
    write_json(manifest,{'repo':REPO,'revision':revision,'api':api,'files':logs,
        'identity':'original full safetensors; complete local file hashes pin content'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--only');p.add_argument('--endpoint',default='https://huggingface.co')
    a=p.parse_args();fetch(a.only,a.endpoint)
