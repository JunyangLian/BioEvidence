"""Download three distinct original weight shards concurrently; no shared writes."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from common import *
from fetch_model import fetch

def worker(index):
    file=f'model-{index:05d}-of-00003.safetensors'
    with (ROOT/f'model-download-shard{index}.log').open('w',encoding='utf-8') as out:
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'fetch_model.py'),'--only',file],
            stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    return {'file':file,'exit_code':p.returncode}

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(worker,(1,2,3)))
    write_json(ROOT/'reports/model_download_workers.json',results)
    if any(r['exit_code'] for r in results):raise RuntimeError('Download failed; preserve logs and partials')
    fetch() # verify complete shards and fetch small config/tokenizer assets
