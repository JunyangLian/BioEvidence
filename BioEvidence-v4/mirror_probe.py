"""Read-only range probe against a documented mirror of the same fixed weights."""
import urllib.request
import urllib.parse
import time
import argparse
from datetime import datetime, timezone
from fetch_model import REPO, DEST
from common import *

def run(byte_count=65536):
    revision=read_json(DEST/'repo_api.json')['revision'];name='model-00003-of-00003.safetensors'
    with (DEST/name).open('rb') as inp:expected=inp.read(byte_count)
    result={'mirror':'https://hf-mirror.com','documentation':'https://hf-mirror.com/',
            'timestamp_utc':datetime.now(timezone.utc).isoformat(),'revision':revision,'file':name,
            'role':'transport probe only; official upstream whole-file SHA remains required','bytes_requested':byte_count}
    started=time.perf_counter()
    try:
        url=f'https://hf-mirror.com/{REPO}/resolve/{revision}/{name}?download=true&v4_probe={byte_count}'
        req=urllib.request.Request(url,headers={'Range':f'bytes=0-{byte_count-1}'})
        with urllib.request.urlopen(req,timeout=30) as r:
            content=r.read(byte_count)
            result.update({'http_status':r.status,'content_range':r.headers.get('Content-Range'),
                           'final_host':urllib.parse.urlsplit(r.geturl()).hostname,
                           'bytes_received':len(content),'same_as_verified_original_prefix':content==expected})
    except Exception as exc:result['error']=f'{type(exc).__name__}: {exc}'
    result['seconds']=time.perf_counter()-started
    write_json(ROOT/f'reports/mirror_probe_{byte_count}.json',result);print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bytes',type=int,default=65536);a=p.parse_args();run(a.bytes)
