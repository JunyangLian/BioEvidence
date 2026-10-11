"""Build final comparisons only from complete locked-config development runs."""
from datetime import datetime, timezone
from analyze import analyze, correct, ratio, cited
from common import *

def run():
    from verify_outputs import run as verify_outputs
    integrity=verify_outputs()
    models=['base_06b','instruct_4b']; data={}; analyses={}; cross={}
    for m in models:
        rows=jsonl(ROOT/f'runs/{m}/dev151/predictions.jsonl')
        assert len(rows)==604 and len({(r['question_id'],r['condition']) for r in rows})==604
        assert len({r['config_fingerprint'] for r in rows})==1
        smoke=read_json(ROOT/f'runs/{m}/smoke10/summary.json')
        assert rows[0]['config_fingerprint']==smoke['config_fingerprint']
        assert all(r['source_split']=='internal_70_30/dev' for r in rows)
        data[m]={(r['question_id'],r['condition']):r for r in rows}
        analyses[m]=analyze(m,'dev151')
    assert set(data[models[0]])==set(data[models[1]])
    joined=[]
    for cond in order.CONDITIONS:
        pairs=[]
        for key in sorted(data[models[0]]):
            if key[1]!=cond:continue
            a=data[models[0]][key];b=data[models[1]][key]
            assert a['gold']==b['gold'] and a['evidence_block']==b['evidence_block'] and a['messages']==b['messages']
            p={'question_id':key[0],'condition':cond,'base_06b_correct':correct(a),'instruct_4b_correct':correct(b),
               'label_changed':a['label']!=b['label'],'answerable_changed':a['answerable']!=b['answerable'],
               'actual_citation_set_changed':cited(a)!=cited(b),'base_cache_key':a['cache_key'],'instruct_cache_key':b['cache_key']}
            pairs.append(p);joined.append(p)
        loss=sum(p['base_06b_correct'] and not p['instruct_4b_correct'] for p in pairs)
        gain=sum(not p['base_06b_correct'] and p['instruct_4b_correct'] for p in pairs)
        cross[cond]={'n_pairs':len(pairs),
            **{k:ratio(sum(p[k] for p in pairs),len(pairs)) for k in ['label_changed','answerable_changed','actual_citation_set_changed']},
            'mcnemar_correct_incorrect_only':v2score.mcnemar_exact(loss,gain)}
    cost={'unique_main_generation_requests':1208,'unique_main_generated_tokens':sum(a['cost']['total_generated_tokens'] for a in analyses.values()),
          'unique_main_generation_seconds':sum(a['cost']['generation_seconds_all_unique'] for a in analyses.values()),
          'note':'Includes the 80 smoke requests once via cache reuse. E7/framework extra requests reported separately; download/install excluded.'}
    device_rows=jsonl(ROOT/'logs/gpu_memory_series.jsonl') if (ROOT/'logs/gpu_memory_series.jsonl').exists() else []
    device_memory={'n_samples':len(device_rows),'observed_peak_used_mib':max((r.get('used_mib',0) for r in device_rows),default=None),
        'scope':'Whole GPU including desktop/other processes; 2-second sampling within active monitor windows, with gaps across interruptions. May miss brief transients. Per-request allocator peaks are separate.'}
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'scope':'Repeated development dev151; order + renumbering intervention',
            'models':analyses,'cross_model':cross,'cost':cost,'whole_device_memory':device_memory,'output_integrity':integrity,'predefined_success_threshold':None,
            'limitations':['No new held-out evaluation','Model differences include scale, model version and instruction training',
                          'No pure position-effect separation','Human sufficiency subset only dev26; single reviewer identity/time unknown',
                          'AI assisted 16 opinions on 2 questions; different reviewers per model; illustrative only, not human truth','Reason output is not direct evidence of internal reasoning',
                          'McNemar comparisons exploratory, no multiplicity adjustment; no macro-F1 significance claim']}
    write_json(ROOT/'reports/development_comparison.json',report)
    write_jsonl(ROOT/'reports/cross_model_pairs.jsonl',joined)
    lines=['# BioEvidence v4 开发对照结果','',
           '本轮为反复使用的 dev151，非新留出评测。固定预算后的证据内容只改变顺序及显示编号；不能分离纯位置效应。',
           '', '604 条历史原始输出的真实离线 harness 评分回放通过，逐条解析及各条件整数计数、分母、accuracy、macro-F1 均无差异。v1 原 structural 入口及其冻结汇总另行保持。',
           '', '在本次dev151上，0.6B无adapter配置几乎全部预测yes，no/maybe召回均为0，accuracy接近参考多数类比例；低标签变化不能解释为可靠推理。4B四条件macro-F1均更高，但maybe precision仍只有约0.14–0.16。同条件跨模型正确/错误McNemar的探索性p为0.3916–1.0；不新增成功门槛，不对macro-F1作显著性声明，也不据此证明无差异或等效。',
           '相对B0，4B的B1/B2/B3分别有31/34/30题标签变化、7/12/8题Answerable变化、64/66/41题实际引用集合变化；0.6B每个对照只有1题标签变化，但引用集合和raw仍有变化。B1结果族优先的4B正确数从86降至85，B2为84，B3为90；没有统一顺序收益，不挑最高条件宣布有效。未改变输入的2题B1及21题B3配对，在两模型中均未出现raw变化。',
           '旧解析器均成功且无越界，但契约问题类型明显不同：0.6B的469条严格机械违规全部为引用字段末尾句号；4B的78条主要是弃答仍引用、或弃答时Label不是maybe。弃答多寡本身不判优劣。人工26题子集中，0.6B各条件不足仍作答14/14；4B为9/14、10/14、11/14、9/14，同时充分却弃答为0/12、1/12、2/12、1/12。这些子集分母不能外推到全部151题。',
           '', '| 模型 | 条件 | 正确/151 | accuracy | macro-F1 | 解析失败 | 引用越界 | 完整契约违规 | 弃答/151 |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in models:
        for cond,p in analyses[m]['per_condition'].items():
            c=p['classification'];lines.append(f"| {m} | {cond} | {c['n_correct']} | {c['accuracy']:.4f} | {c['macro_f1']:.4f} | {p['parse_failure']['num']} | {p['citation_out_of_range']['num']} | {p['complete_contract_violation']['num']} | {p['abstention_behavior']['num']} |")
    lines+=['','| 模型 | 条件 | 标签 | support | precision | recall | F1 |',
            '|---|---|---|---:|---:|---:|---:|']
    def value(x):return 'N/A' if x is None else f'{x:.4f}'
    for m in models:
        for cond,p in analyses[m]['per_condition'].items():
            for label,c in p['classification']['per_class'].items():
                lines.append(f"| {m} | {cond} | {label} | {c['support']} | {value(c['precision'])} | {value(c['recall'])} | {value(c['f1'])} |")
    lines+=['','| 模型 | 条件 | 预测标签分布（含失败时解析字段） | 严格契约问题类型计数 | 仅引用字段末尾句号语法偏离 |',
            '|---|---|---|---|---:|']
    for m in models:
        for cond,p in analyses[m]['per_condition'].items():
            labels='; '.join(f'{k}={v}' for k,v in p['predicted_label_distribution'].items())
            issues='; '.join(f'{k}={v}' for k,v in p['complete_contract_issue_counts'].items()) or '0'
            lines.append(f"| {m} | {cond} | {labels} | {issues} | {p['citation_terminal_period_only']['num']}/{p['citation_terminal_period_only']['den']} |")
    lines+=['','分类按原 v2 口径包含全部151条，invalid计错；固定标签 yes/no/maybe，三类均有参考支持。完整契约机械诊断与历史解析状态分别报告：四个非空行、字段顺序、Label/Answerable严格单词、引用字段严格为None或逗号分隔E编号、原解析器的citation_issues及生成失败。引用列表末尾句号也计为严格语法偏离；不能把这些记录都解释成缺字段、引用越界或语义不支持。该机械诊断不核验Reason的生物医药语义支持，不覆盖所有可能的自然语言约束。弃答率仅作行为诊断。逐类表现、人工参考的覆盖/分母、长度、延迟、显存和失败案例见对应 analysis.json。',
            '', '| 模型 | 对照 B0 | 输入改变/未变 | 标签变化 | Answerable变化 | 实际引用集合变化 |',
            '|---|---|---:|---:|---:|---:|']
    for m in models:
        for cond,p in analyses[m]['paired'].items():
            a=p['all'];lines.append(f"| {m} | {cond} | {p['input_changed']['n_pairs']}/{p['input_unchanged']['n_pairs']} | {a['label_changed']['num']}/151 | {a['answerable_changed']['num']}/151 | {a['actual_citation_set_changed']['num']}/151 |")
    lines+=['','| 模型 | 对照B0 | 输入分层 | 配对数 | 标签变化 | Answerable变化 | 实际引用集合变化 | raw变化 |',
            '|---|---|---|---:|---:|---:|---:|---:|']
    for m in models:
        for cond,p in analyses[m]['paired'].items():
            for stratum in ('input_changed','input_unchanged'):
                s=p[stratum];n=s['n_pairs']
                counts=[f"{s[k]['num']}/{n}" if n else 'N/A (0/0)' for k in ('label_changed','answerable_changed','actual_citation_set_changed','raw_changed')]
                lines.append(f"| {m} | {cond} | {stratum} | {n} | {' | '.join(counts)} |")
    lines+=['','| 同条件跨模型配对 | 标签变化/151 | Answerable变化/151 | 实际引用集合变化/151 | 正确→错 b / 错→正确 c | McNemar p（探索性） |',
            '|---|---:|---:|---:|---:|---:|']
    for cond,p in cross.items():
        mc=p['mcnemar_correct_incorrect_only']
        lines.append(f"| {cond} | {p['label_changed']['num']} | {p['answerable_changed']['num']} | {p['actual_citation_set_changed']['num']} | {mc['b']}/{mc['c']} | {mc['p_exact']} |")
    lines+=['','| 模型 | 条件 | 人工覆盖/151 | 不足仍作答/14 | 充分却弃答/12 | 人工子集历史解析/生成失败（不足/充分） |',
            '|---|---|---:|---:|---:|---:|']
    for m in models:
        for cond,p in analyses[m]['per_condition'].items():
            cov=p['human_coverage'];u=p['unsupported_answer'];w=p['wrong_abstention'];f=p['human_subset_failures']
            lines.append(f"| {m} | {cond} | {cov['num']}/{cov['den']} | {u['num']}/{u['den']} | {w['num']}/{w['den']} | {f['insufficient']}/{f['sufficient']} |")
    lines+=['','人工充分性参考只覆盖固定26题，参考充分/不足分别为12/14；每条件保持这两个完整分母。历史解析或生成失败单列，不自动记为恰当作答或弃答；原解析器允许的契约矛盾另见完整契约诊断，仍可出现在此行为表。该子集不代表全部151题，历史文献身份代理也不代替充分性参考。']
    lines+=['','配对 JSON 同时保存输入变化/未变化分层、原始输出变化、显示编号与稳定chunk引用集合。McNemar仅检验同题正确/错误配对，未用于macro-F1；多项比较均为探索性，未做多重性校正，也未新增成功门槛。',
            '', '| 模型 | 唯一请求 | 生成token | 生成秒 | 峰值已分配/保留GiB |', '|---|---:|---:|---:|---:|']
    for m in models:
        c=analyses[m]['cost'];lines.append(f"| {m} | {c['requests']} | {c['total_generated_tokens']} | {c['generation_seconds_all_unique']:.1f} | {c['peak_allocated_gib']:.3f}/{c['peak_reserved_gib']:.3f} |")
    lines+=['','实际加载dtype见output_integrity_dev151.json：harness从模型对象读取的dtype为torch.bfloat16。共享配置为NF4 4-bit、双重量化、bfloat16计算、batch_size=1、最大上下文2048、输出160、greedy。harness本地model_revision=main只是加载默认元数据，不能作为权重来源；完整本地hash和4B固定revision记录在各模型config.json及download_manifest.json。']
    lines+=['','上述成本包含小样本缓存一次，不重复计费；安装、下载、模型加载、官方框架冒烟及E7回归另记。E7不混入主比较。',
            f"CUDA allocator峰值为生成请求期间实际读数；另有活动监测窗口内2秒间隔整卡采样 {device_memory['n_samples']} 次，观察峰值 {device_memory['observed_peak_used_mib']}MiB，包含桌面等其它进程且可能漏掉短暂峰值。中断之间存在采样空窗；原序列见logs/gpu_memory_series.jsonl。",
            '', '0.6B基座与4B Instruct的差异同时涉及模型规模、版本与指令训练，不能归因于单一规模，也不能据此证明微调效果。引用合法、结果族引用、语义支持及标签正确分别报告。人工充分性参考只覆盖26题（不足14/充分12），其余未知不记通过。',
            '分类参考来自原问题标签，标签正确不证明给定检索证据支持该答案或理由；maybe是原分类标签，不等于证据不足。Answerable行为另按人工充分性子集诊断。',
            '', '两批当前任务内子agent的16条盲化AI辅助意见、48处定位已锁定后解封，只覆盖同样2题。精确agent模型运行标识无法取得，记录unknown。每模型由不同agent评定，审核者与模型混杂；此便利小子集不用于总体比例、人工真值或模型优劣结论。记录与限制见ai_assisted/AI_REVIEW.md。',
            '', '可运行命令见 README.md；依赖及源码来源见 environment.json、requirements-lock.txt、requirements-hashed.txt、reports/source_commits.json；历史封存保护见 reports/historical_protection.json。']
    (ROOT/'reports/V4_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Complete comparison report generated:',cost)

if __name__=='__main__':run()
