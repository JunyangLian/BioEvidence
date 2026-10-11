"""Keep V4_STATUS current during the already-authorized finite evaluation run."""
import re
import time
from datetime import datetime, timezone, timedelta
from common import ROOT, read_json

def run():
    started=time.monotonic(); status=ROOT/'V4_STATUS.md'
    while time.monotonic()-started<3*3600:
        progress={}
        for model in ('base_06b','instruct_4b'):
            path=ROOT/f'logs/generate_model_{model}_n_151.log'
            matches=re.findall(rf'^{model} (\d+) / 604 ',path.read_text(encoding='utf-8').replace('\r',''),re.M) if path.exists() else []
            summary=ROOT/f'runs/{model}/dev151/summary.json'
            progress[model]=read_json(summary)['n'] if summary.exists() else int(matches[-1]) if matches else 0
        stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S 北京时间')
        text=status.read_text(encoding='utf-8')
        marker='<!-- LIVE_PROGRESS -->'
        text=text.split(marker)[0].rstrip()+'\n\n'+marker+'\n'
        text+=f'运行监测 {stamp}：0.6B {progress["base_06b"]}/604，4B {progress["instruct_4b"]}/604。数字包含已复用smoke缓存；阶段报告完成以真实summary和pipeline_complete为准。\n'
        status.write_text(text,encoding='utf-8')
        if (ROOT/'reports/pipeline_complete.json').exists():return
        time.sleep(30)

if __name__=='__main__':run()
