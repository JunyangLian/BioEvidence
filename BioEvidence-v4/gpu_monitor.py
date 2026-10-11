"""Read-only whole-device memory sampling alongside gated generation pipeline."""
import subprocess
import time
from datetime import datetime, timezone
from common import *

def run():
    path=ROOT/'logs/gpu_memory_series.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();maximum=0; count=0;baseline=None
    with path.open('a',encoding='utf-8') as out:
        while time.monotonic()-started<6*3600:
            result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],
                capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
            row={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'query_returncode':result.returncode,
                 'raw':result.stdout.strip(),'scope':'whole GPU; includes desktop/other processes, not model-only CUDA allocator'}
            if result.returncode==0:
                used,total=[int(x.strip()) for x in result.stdout.strip().splitlines()[0].split(',')]
                row.update({'used_mib':used,'total_mib':total});maximum=max(maximum,used)
                if baseline is None:baseline=used
            out.write(json.dumps(row)+'\n');out.flush();count+=1
            if (ROOT/'reports/pipeline_complete.json').exists():break
            time.sleep(2)
    write_json(ROOT/'reports/gpu_device_memory.json',{'n_samples':count,'interval_seconds':2,'baseline_mib':baseline,
        'observed_peak_used_mib':maximum,'scope':'whole GPU including other processes; sampling may miss short transients',
        'model_allocator_peaks':'reported separately per request in predictions.jsonl'})
    print('GPU device monitor complete',count,maximum,'MiB')

if __name__=='__main__':run()
