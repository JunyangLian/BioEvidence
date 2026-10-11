"""Within-model deltas; predefined conditions and failures retained."""
from common import *
from analyze import analyze,correct,cited,ratio
from datetime import datetime,timezone
MODELS=['base_06b','e7_06b','instruct_4b','tuned_4b']

def run(b0=False):
    from integrity import run as verify
    scope='B0_dev151' if b0 else 'dev151';integrity=verify(scope)
    analyses={m:analyze(m,scope) for m in MODELS}
    data={m:{(r['question_id'],r['condition']):r for r in jsonl(ROOT/f'runs/{m}/{scope}/predictions.jsonl')} for m in MODELS}
    assert all(set(data[m])==set(data[MODELS[0]]) for m in MODELS)
    paired={};joined=[]
    conditions=[order.CONDITIONS[0]] if b0 else order.CONDITIONS
    for raw,tuned in [('base_06b','e7_06b'),('instruct_4b','tuned_4b')]:
        entry={}
        for cond in conditions:
            ps=[]
            for key in sorted(data[raw]):
                if key[1]!=cond:continue
                a,b=data[raw][key],data[tuned][key]
                for k in ['gold','messages','evidence_block','display_to_chunk','rendered_prompt','input_token_ids']:
                    assert a[k]==b[k],('Within-model input mismatch',raw,tuned,key,k)
                p={'question_id':key[0],'condition':cond,'untuned':raw,'tuned':tuned,
                    'untuned_correct':correct(a),'tuned_correct':correct(b),'label_changed':a['label']!=b['label'],
                    'answerable_changed':a['answerable']!=b['answerable'],'actual_citation_set_changed':cited(a)!=cited(b),
                    'untuned_cache_key':a['cache_key'],'tuned_cache_key':b['cache_key']}
                ps.append(p);joined.append(p)
            loss=sum(p['untuned_correct'] and not p['tuned_correct'] for p in ps)
            gain=sum(not p['untuned_correct'] and p['tuned_correct'] for p in ps)
            a=analyses[raw]['per_condition'][cond];b=analyses[tuned]['per_condition'][cond]
            entry[cond]={'n_pairs':len(ps),'delta_accuracy':round(b['classification']['accuracy']-a['classification']['accuracy'],4),
                'delta_macro_f1':round(b['classification']['macro_f1']-a['classification']['macro_f1'],4),
                'delta_contract_violations':b['complete_contract_violation']['num']-a['complete_contract_violation']['num'],
                'delta_unsupported_answer_on_human14':b['unsupported_answer']['num']-a['unsupported_answer']['num'],
                'delta_wrong_abstention_on_human12':b['wrong_abstention']['num']-a['wrong_abstention']['num'],
                **{k:ratio(sum(p[k] for p in ps),len(ps)) for k in ['label_changed','answerable_changed','actual_citation_set_changed']},
                'mcnemar_correct_incorrect_only':v2score.mcnemar_exact(loss,gain)}
        paired[f'{raw}_to_{tuned}']=entry
    tr=read_json(ROOT/'runs/training/full/report.json');new=analyses['tuned_4b']['cost']
    target_audit=read_json(ROOT/'reports/historical_target_distribution.json')
    cost={'comparison_rows':sum(len(v) for v in data.values()),'historical_reuse_rows':sum(bool(r.get('provenance')) for ds in data.values() for r in ds.values()),
        'new_unique_generation_requests':new['requests'],'new_generation_tokens':new['total_generated_tokens'],
        'new_generation_seconds':new['generation_seconds_all_unique'],'training_seconds':tr['train_seconds'],
        'training_updates':tr['global_step'],'training_peak_allocated_gib':tr['peak_allocated_gib'],
        'training_peak_reserved_gib':tr['peak_reserved_gib'],'historical_missing_actual_token_count_rows':len(data['e7_06b']),
        'new_generation_peak_allocated_gib':new['peak_allocated_gib'],'new_generation_peak_reserved_gib':new['peak_reserved_gib'],
        'boundary':'Historical per-item timings are provenance only, not newly incurred cost; E7 actual tokens/stop/per-item GPU unknown. Smoke counted once through cache. Installation/download/load excluded.'}
    ai_path=ROOT/'ai_assisted/summary.json'
    ai=read_json(ai_path) if ai_path.exists() else None
    semantic_note=('AI-assisted blinded illustrative review: two development questions, eight cases, sixteen opinions; locked before model-map joining. Not independent human truth or population evidence. See ai_assisted/AI_REVIEW.md.'
        if ai else 'No completed new V5 semantic review; mechanical results cannot establish reason/citation faithfulness')
    result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'scope':scope,'models':analyses,'within_model':paired,
        'historical_target_distribution':target_audit,
        'cost':cost,'integrity':integrity,'predefined_success_threshold':None,
        'semantic_review':semantic_note,'ai_assisted_review':ai,
        'limits':['Repeated dev151, not fresh holdout','Fixed final three epochs, no dev checkpoint selection',
            'Same582 historical targets; proxy limitations preserved','Starting-model training histories differ, not pure scale effect',
            'Order plus renumbering','Single seed','Human sufficiency only26, reviewer/time unknown',
            'E7 historical direct-HF backend; migration verified on10, not604 regenerated',
            'Question gold direction may penalize appropriate maybe/no-answer under insufficient retrieved evidence; sufficiency assessed separately',
            'McNemar exploratory correct/incorrect only, no macro-F1 significance or multiplicity adjustment']}
    suffix='_B0' if b0 else ''
    write_json(ROOT/f'reports/development_comparison{suffix}.json',result)
    write_jsonl(ROOT/f'reports/within_model_pairs{suffix}.jsonl',joined)
    lines=['# BioEvidence V5：领域适配开发对照'+('（B0阶段）' if b0 else ''),'',
        '0.6B使用冻结E7；4B独立环境使用完全相同582条历史目标，固定3轮/219更新，采用最终checkpoint。最长原生训练941 token，相同TRL追加EOS后942，582条真实监督掩码均通过，无证据或监督正文截断。历史训练报告表头Task A标识与实际Task B消息不一致，按实际消息与loss mask核验，封存表头未改。',
        'dev151已反复使用，仅为探索性开发配对对照。未用它选checkpoint、调参或改目标；未运行历史test/V3验收。','',
        '| 配置 | 条件 | 正确/151 | accuracy | macro-F1 | 解析失败 | 引用越界 | 严格机械契约违规 | 弃答/151 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in MODELS:
        for cond in conditions:
            p=analyses[m]['per_condition'][cond];c=p['classification']
            lines.append(f"| {m} | {cond} | {c['n_correct']} | {c['accuracy']:.4f} | {c['macro_f1']:.4f} | {p['parse_failure']['num']} | {p['citation_out_of_range']['num']} | {p['complete_contract_violation']['num']} | {p['abstention_behavior']['num']} |")
    lines+=['','| 同一起始模型：微调后减微调前 | 条件 | Δaccuracy | Δmacro-F1 | Δ契约违规数 | Δ不足仍作答/14 | Δ充分却弃答/12 | 正确→错/错→正确 | McNemar探索性p |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for pair,cs in paired.items():
        for cond,p in cs.items():
            mc=p['mcnemar_correct_incorrect_only']
            lines.append(f"| {pair} | {cond} | {p['delta_accuracy']:+.4f} | {p['delta_macro_f1']:+.4f} | {p['delta_contract_violations']:+d} | {p['delta_unsupported_answer_on_human14']:+d} | {p['delta_wrong_abstention_on_human12']:+d} | {mc['b']}/{mc['c']} | {mc['p_exact']} |")
    for pair,cs in paired.items():
        p=cs['B0_original']
        lines+=['',f"B0：{pair} 的macro-F1变化 {p['delta_macro_f1']:+.4f}、accuracy变化 {p['delta_accuracy']:+.4f}；严格机械契约违规变化 {p['delta_contract_violations']:+d}。人工不足子集仍作答变化 {p['delta_unsupported_answer_on_human14']:+d}/14，充分子集错误弃答变化 {p['delta_wrong_abstention_on_human12']:+d}/12。各指标分别解释，不将分类变化自动等同证据使用收益。"]
    lines+=['','| 配置 | 条件 | 标签 | support | precision | recall | F1 |','|---|---|---|---:|---:|---:|---:|']
    fmt=lambda x:'N/A' if x is None else f'{x:.4f}'
    for m in MODELS:
        for cond in conditions:
            for lab,c in analyses[m]['per_condition'][cond]['classification']['per_class'].items():
                lines.append(f"| {m} | {cond} | {lab} | {c['support']} | {fmt(c['precision'])} | {fmt(c['recall'])} | {fmt(c['f1'])} |")
    lines+=['','| 配置 | 条件 | 标签分布 | 严格机械违规类型 | 不足仍作答/14 | 充分却弃答/12 | 人工子集解析/生成失败（不足/充分） |',
        '|---|---|---|---|---:|---:|---:|']
    for m in MODELS:
        for cond in conditions:
            p=analyses[m]['per_condition'][cond];f=p['human_subset_failures']
            lines.append(f"| {m} | {cond} | {p['predicted_label_distribution']} | {p['complete_contract_issue_counts']} | {p['unsupported_answer']['num']}/14 | {p['wrong_abstention']['num']}/12 | {f['insufficient']}/{f['sufficient']} |")
    if not b0:
        lines+=['','| 配置 | 对照B0 | 输入分层 | 配对数 | 标签变化 | Answerable变化 | 实际chunk引用集合变化 | raw变化 |',
            '|---|---|---|---:|---:|---:|---:|---:|']
        for m in MODELS:
            for cond,p in analyses[m]['paired'].items():
                for layer in ['input_changed','input_unchanged']:
                    a=p[layer];n=a['n_pairs']
                    counts=[f"{a[k]['num']}/{n}" if n else 'N/A(0/0)' for k in ['label_changed','answerable_changed','actual_citation_set_changed','raw_changed']]
                    lines.append(f"| {m} | {cond} | {layer} | {n} | {' | '.join(counts)} |")
    lines+=['','历史目标机械分布：Answerable=yes 342条（yes190/no116/maybe36），Answerable=no 240条（全部maybe）；正例单引用E1/E2/E3分别147/130/65。保留原目标，不将其分布等同语义正确；训练目标标签分布与开发参考分布不同也不能自行修正。',
        '分类沿用冻结v2入口：全部151条为分母，invalid计错，固定yes/no/maybe，support为83/51/17；v1口径另存，未统一历史分母。严格机械契约诊断与历史解析状态分开；引用末尾句号计为语法偏离，不能全部解释为语义不忠实。maybe与不足分开，弃答率不预设高低为好。人工充分性只覆盖26题（不足14/充分12），其余未知不自动通过，失败保留分母并单列。',
        '分类参考是原问题方向标签，给定检索证据不足时恰当输出maybe/Answerable=no也可能被该分类指标记错。因此分类分数与恰当弃答分别解释，不能为迁移更改原标签或分母。',
        '理由支持、引用支持与标签正确是不同指标。机械引用合法不能证明引用忠实，输出理由不是内部推理证据。无RESULTS不自动不足；训练342条Answerable=yes中149条无结果族是结构诊断，不等于149条错误目标。',
        ('两位AI辅助审核者各自覆盖四组同样2题B0，8个案例/16条意见，42处原文证据定位校验后先锁定再解封模型映射。仅作案例解释，不是真实专家或独立人工真值，不外推模型语义收益。复核中理由关键主张支持改善仍可能伴随理由与标签不一致。完整分歧、保留意见及实际模型标识unknown/unavailable见ai_assisted/AI_REVIEW.md。' if ai else '新增V5语义复核尚未完成。'),
        '','| 成本 | 实际值 |','|---|---:|']
    for k,v in cost.items():lines.append(f'| {k} | {v} |')
    lines+=['','复用V4 raw1208条与V2冻结E7 604条；输入、权重、提示、解析及冻结分数逐条核验。E7 B0 raw与P7 151条完全一致，V4另有10条新旧HF/harness迁移回归。E7实际生成token、停止及逐请求显存为unknown；输出重token化长度单列，不冒充实际生成长度。历史后端不同，不能声称604条全部已新生成验证。',
        '两起始模型规模、版本、指令训练历史不同，Δ描述各自领域适配变化，两个Δ不能隔离纯规模效应。顺序含重新编号，不能隔离纯位置效应。全部预注册条件报告，按输入/实现/资源门槛扩跑，不按分数筛选。单训练种子，无稳定性声明；McNemar仅正确/错误探索性配对，未多重校正，不用于macro-F1显著性或证明等效。',
        '训练对齐见E7_training_alignment.json：实际共同参数逐项一致；相同LoRA秩和模块类别仍对应E7 5,046,272与4B 16,515,072个可训练参数，原生模板和token长度不同。历史不存中间checkpoint，V5保存仅供恢复。历史P0版本记录不等于完整P6二进制快照，不声称相同计算预算或训练逐位可复现。',
        '','逐条完整输入、稳定chunk映射、raw、解析、错误及指纹见runs/<model>/dev151/predictions.jsonl；失败和分层配对见analysis.json/pairs.jsonl/failure_cases.jsonl。依赖来源、源码hash、adapter完整hash和命令见environment.json、requirements-hashed.txt、训练report.json、README.md。历史保护见reports/historical_protection.json。']
    (ROOT/f'reports/V5_REPORT{suffix}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if not b0:
        from cases import run as casebook
        casebook()
        finding_lines=['# V5 主要发现','',
            '四组、四顺序开发对照已完成。4B以相同582条历史E7目标完成固定3轮/219更新；2416条比较记录中1812条经过逐条核验复用，本轮新增604条生成。以下B0是预定原顺序，完整四条件均见V5_REPORT.md。','',
            '| B0配置 | accuracy | macro-F1 | 严格机械契约违规/151 | 不足仍作答/14 | 充分却弃答/12 |',
            '|---|---:|---:|---:|---:|---:|']
        for m in MODELS:
            p=analyses[m]['per_condition']['B0_original'];c=p['classification']
            finding_lines.append(f"| {m} | {c['accuracy']:.4f} | {c['macro_f1']:.4f} | {p['complete_contract_violation']['num']} | {p['unsupported_answer']['num']} | {p['wrong_abstention']['num']} |")
        for pair,cs in paired.items():
            p=cs['B0_original']
            finding_lines+=['',f"{pair}：accuracy {p['delta_accuracy']:+.4f}，macro-F1 {p['delta_macro_f1']:+.4f}，严格机械违规 {p['delta_contract_violations']:+d}，不足仍作答 {p['delta_unsupported_answer_on_human14']:+d}/14，充分却弃答 {p['delta_wrong_abstention_on_human12']:+d}/12。分类、契约和弃答的变化应分别解释。"]
        finding_lines+=['','| 配置 | 四条件macro-F1范围 | B1/B2/B3相对B0标签变化/151 | B1/B2/B3实际引用集合变化/151 |',
            '|---|---:|---|---|']
        for m in MODELS:
            f1=[p['classification']['macro_f1'] for p in analyses[m]['per_condition'].values()]
            labels='/'.join(str(analyses[m]['paired'][c]['all']['label_changed']['num']) for c in order.CONDITIONS[1:])
            citations='/'.join(str(analyses[m]['paired'][c]['all']['actual_citation_set_changed']['num']) for c in order.CONDITIONS[1:])
            finding_lines.append(f"| {m} | {min(f1):.4f}–{max(f1):.4f} | {labels} | {citations} |")
        finding_lines+=['','顺序包含重新编号，引用比较基于实际chunk集合。B1有2题、B3有21题输入未改变，完整报告另分层；汇总变化不能全部归因于位置。',
            '',f"实测成本：训练{cost['training_seconds']/60:.2f}分钟；604条唯一新增生成累计{cost['new_generation_seconds']/60:.2f}分钟、{cost['new_generation_tokens']} token（不含安装、加载和校验）。训练CUDA分配峰值{cost['training_peak_allocated_gib']:.3f}GiB，生成{cost['new_generation_peak_allocated_gib']:.3f}GiB；整卡含桌面进程的15秒采样另存，不能与allocator峰值混用。",
            '', '边界：dev151已反复使用；单训练种子、无dev选checkpoint。人工充分性只覆盖26题。两题AI辅助复核只解释案例，不是真实专家或独立人工真值。E7历史实际token/停止/逐请求显存unknown。不同起始模型的版本和指令训练历史不同，不能隔离纯参数规模效应。无新留出评测、无历史test或V3验收运行；V1–V4保护结果与交付hash另存。']
        (ROOT/'reports/V5_FINDINGS.md').write_text('\n'.join(finding_lines)+'\n',encoding='utf-8')
    print('Four-group report generated',scope,cost,flush=True)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--b0-only',action='store_true');a=p.parse_args();run(a.b0_only)
