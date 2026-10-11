"""Finite V5 status/device monitoring; whole GPU is separate from allocator peak."""
from common import *
from datetime import datetime,timezone,timedelta
import time,subprocess

def run():
    began=time.monotonic()
    while time.monotonic()-began<28800:
        full=ROOT/'runs/training/full/report.json';steps=ROOT/'runs/training/full/steps.jsonl'
        n=read_json(full)['global_step'] if full.exists() else jsonl(steps)[-1]['global_step'] if steps.exists() else 0
        completed=(ROOT/'reports/pipeline_complete.json').exists()
        txt=f"""# BioEvidence V5 状态

更新时间：{datetime.now(timezone(timedelta(hours=8))).isoformat()}

已完成：独立venv及依赖锁（核心未升级，pip check通过）；582条训练题与dev无交集；原生941 token/含TRL EOS942；582条实际loss mask；完整最短/最长两次优化器更新；604条历史raw经harness真实评分一致性及v1分母；7项补充风险测试；1812条历史预测的权重/证据/输入/解析复用核验。

固定协议：历史582目标、3轮/219更新、最终checkpoint；不清洗扩增或dev选优。各起始模型前后比较，非纯规模效应；只用反复开发dev151，test/V3验收/V1–V4不写入。

训练：{n}/219更新，{'已完成' if full.exists() else '进行中'}。两次优化器前接口核验失败（字段名、TRL追加EOS）已保存并修复；没有OOM或通过截断规避。
"""
        for scope,total in [('smoke10',10),('B0_dev151',151),('dev151',604)]:
            path=ROOT/f'runs/tuned_4b/{scope}/summary.json'
            if path.exists():txt+=f"\n4B adapter {scope}：{read_json(path)['n']}/{total}，真实summary已保存。\n"
        txt+='\n矩阵2416=历史1812+新604（smoke/B0缓存计一次）。扩展依据完整性/预注册预算，非分数优劣。E7实际token/停止/逐请求显存unknown。\n'
        cfg=ROOT/'runs/tuned_4b/config.json'
        if cfg.exists():
            fp=read_json(cfg)['config_fingerprint'];cache=ROOT/'cache/generation/tuned_4b'/fp
            count=len(list(cache.glob('*.json'))) if cache.exists() else 0
            txt+=f'\n4B adapter当前配置唯一已记录请求：{count}/604（包括已完成B0及smoke一次，不是循环已遍历条数）。\n'
        pending=[]
        if not full.exists():pending.append('固定三轮训练')
        if not (ROOT/'reports/development_comparison_B0.json').exists():pending.append('四组B0生成/报告')
        if not (ROOT/'reports/development_comparison.json').exists():pending.append('全顺序生成/报告')
        if not completed:pending.append('最终封存和交付检查')
        txt+=f"\n整体：{'完成；最终报告和封存检查见reports' if completed else '推进中；未完成：'+ '、'.join(pending)}。\n"
        (ROOT/'V5_STATUS.md').write_text(txt,encoding='utf-8')
        try:
            p=subprocess.run(['nvidia-smi','--query-gpu=timestamp,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=10)
            if p.returncode==0:
                a=p.stdout.strip().split(',');r={'timestamp_device_local':a[0].strip(),'used_mib':int(a[1]),'gpu_util_percent':int(a[2]),'scope':'Whole GPU includes other processes; 15-second samples may miss transients'}
                with (ROOT/'logs/gpu_memory_series.jsonl').open('a',encoding='utf-8') as f:f.write(__import__('json').dumps(r)+'\n')
        except Exception as e:write_json(ROOT/'logs/gpu_monitor_error.json',{'error':str(e)})
        if completed:return
        time.sleep(15)
if __name__=='__main__':run()
