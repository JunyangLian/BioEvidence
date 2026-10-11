"""Record completion only after full real runs and required integrity reports."""
from datetime import datetime, timezone, timedelta
from common import *

def run():
    assert read_json(ROOT/'reports/pipeline_complete.json')['completed']
    protection=read_json(ROOT/'reports/historical_protection.json');assert protection['passed']
    parity=read_json(ROOT/'reports/scoring_parity.json');assert parity['passed']
    report=read_json(ROOT/'reports/development_comparison.json')
    integrity=read_json(ROOT/'reports/output_integrity_dev151.json');assert integrity['passed']
    ai=read_json(ROOT/'ai_assisted/cross_model_summary.json')
    samples=jsonl(ROOT/'logs/gpu_memory_series.jsonl')
    write_json(ROOT/'reports/gpu_device_memory.json',{'n_samples':len(samples),'nominal_interval_seconds':2,
        'observed_peak_used_mib':max((r.get('used_mib',0) for r in samples),default=None),
        'scope':'All saved whole-device monitor windows; includes desktop/other processes, gaps across interruptions, and may miss brief transients. Model CUDA allocator peaks separate.'})
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M 北京时间')
    text=['# BioEvidence v4 状态','',stamp+'：本轮标准化接入与开发对照已完成。','',
        '- v4独立环境已安装并锁定；官方arc_easy 5条框架冒烟、CUDA/bitsandbytes真实前向通过。',
        '- 真实历史开发输出604条离线评分回放通过，逐条解析/错误、整数计数/分母、accuracy及原固定标签macro-F1无差异；v1原结构入口另验证。不是合成接口测试替代。',
        '- E7迁移回归10/10匹配历史冻结原文及直接Transformers输出；仅回归，不混为基座。',
        '- 两主模型各151题四条件604条，合计1208唯一请求；完整提示/token、raw、解析/错误、稳定chunk映射、停止/预算、耗时/显存和缓存键已保存。',
        '- 两模型所有实际输出再次独立核验源装配、模板/token、缓存原文、历史解析及真实harness汇总一致，无额外模型调用。',
        f"- 历史保护复验：{protection['n_hashed']}文件SHA256无变化、无新增/缺失、写入时间无变化；v1冻结清单23/23一致。",
        f"- AI辅助意见{ai['n_opinions']}条/{ai['n_unique_questions']}题，48定位先锁定再解封；不同模型由不同AI子agent复核，非人工真值、不支持总体或模型优劣结论。精确agent模型标识unknown。",'',
        '| 模型 | 条件 | 正确/151 | accuracy | macro-F1 | 解析失败 | 引用越界 | 严格契约机械违规 | 弃答/151 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for m,a in report['models'].items():
        for c,p in a['per_condition'].items():
            v=p['classification']
            text.append(f"| {m} | {c} | {v['n_correct']} | {v['accuracy']:.4f} | {v['macro_f1']:.4f} | {p['parse_failure']['num']} | {p['citation_out_of_range']['num']} | {p['complete_contract_violation']['num']} | {p['abstention_behavior']['num']} |")
    text+=['','严格契约机械违规包含引用字段末尾句号，不能与解析失败、越界或语义不支持混称。原评分分母/公式未更改；人工充分性仅覆盖26题（充分12/不足14），未知不记通过。',
        f"唯一主生成总成本：{report['cost']['unique_main_generated_tokens']} token、{report['cost']['unique_main_generation_seconds']:.1f}生成秒；已包含80条smoke一次，不重复计缓存。下载、加载、框架/E7回归另记。",
        '', '4B在176条处会话中断后从缓存续跑，前段日志与剩余428请求成本登记保留。网络TLS/EOF及CUDA wheel获取问题的有限尝试和替代来源核验均有记录。',
        '', '交付：reports/V4_REPORT.md、reports/development_comparison.json、runs/{base_06b,instruct_4b}/dev151逐条及analysis、README.md真实命令、requirements-lock.txt及requirements-hashed.txt、source_inventory.json、ai_assisted/AI_REVIEW.md。',
        '', '边界：反复使用的dev151，非新留出；顺序＋重新编号，不分离纯位置效应；两模型差异同时涉及规模/版本/指令训练，不证明单一规模或微调效果。McNemar只针对同题正确/错误配对，探索性无多重性校正；没有新增成功门槛。',
        '', '未完成项：本轮要求范围内无。无须用户解决的阻塞。停止于本轮完成节点，不训练、不启动27B、不运行历史test/v3验收，不自动新增留出评测。']
    (ROOT/'V4_STATUS.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    files=[]
    for pattern in ('*.py','*.md','requirements*.txt','environment.json','source_inventory.json','config/*.json','reports/*.json','reports/*.md','runs/*/config.json','runs/*/dev151/*.json','runs/*/dev151/*.jsonl','ai_assisted/*.json','ai_assisted/*.md','ai_assisted/batch2/*.json'):
        files.extend(ROOT.glob(pattern))
    manifest={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(set(files))
        if p.is_file() and p.name not in ('delivery_manifest.json','gpu_device_memory.json')}
    write_json(ROOT/'reports/delivery_manifest.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'v4 implementation, source baseline, configurations, locked dependency/environment files, completed outputs, reports and AI reviews. Weights full hashes separately in model run config identities.',
        'files':manifest,'completed_main_outputs':1208,'history_unchanged':True})
    print('Final status and delivery hashes recorded:',len(manifest),'files')

if __name__=='__main__':run()
