"""All conditions, denominators and paired correct/incorrect diagnostics."""
import argparse
import statistics
import re
from collections import Counter
from common import *

def ratio(num,den):return {'num':num,'den':den,'rate':round(num/den,4) if den else None}
def correct(r):return r['status']=='ok' and r['label']==r['gold']
def cited(r):return {r['display_to_chunk'][f'E{x}'] for x in r.get('citations',[]) if f'E{x}' in r['display_to_chunk']}
def strict_issues(r):
    lines=[l.strip() for l in (r['raw_output'] or '').splitlines() if l.strip()]
    issues=list(r.get('citation_issues',[]))
    if len(lines)!=4:issues.append('not_exactly_four_nonempty_lines')
    if len(lines)==4 and not all(lines[i].lower().startswith(p.lower()) for i,p in enumerate(['Label:','Reason:','Citations:','Answerable:'])):
        issues.append('wrong_field_order')
    if len(lines)==4 and lines[0].lower().startswith('label:') and not re.fullmatch(r'Label:\s*(?:yes|no|maybe)',lines[0],re.IGNORECASE):
        issues.append('label_field_not_single_contract_word')
    if len(lines)==4 and lines[3].lower().startswith('answerable:') and not re.fullmatch(r'Answerable:\s*(?:yes|no)',lines[3],re.IGNORECASE):
        issues.append('answerable_field_not_single_contract_word')
    if len(lines)==4 and lines[2].lower().startswith('citations:'):
        content=lines[2].split(':',1)[1].strip()
        if not re.fullmatch(r'(?:None|E\d+(?:\s*,\s*E\d+)*)',content,re.IGNORECASE):
            issues.append('citation_field_not_comma_separated_ids_or_None')
    if r['status']!='ok':issues.append('parse_or_generation_failure')
    return issues
def distribution(nums):
    if not nums:return None
    xs=sorted(nums)
    return {'n':len(xs),'min':xs[0],'p50':statistics.median(xs),'p90':xs[min(len(xs)-1,int(.90*(len(xs)-1)))],
            'p95':xs[min(len(xs)-1,int(.95*(len(xs)-1)))],'p99':xs[min(len(xs)-1,int(.99*(len(xs)-1)))],
            'max':xs[-1],'mean':statistics.mean(xs),'total':sum(xs)}

def analyze(model_key,scope):
    run_dir=ROOT/'runs'/model_key/scope
    rows=jsonl(run_dir/'predictions.jsonl')
    refs={r['question_id']:r for r in read_json(ROOT/'data/human_dev26_reference.json')}
    by={c:{r['question_id']:r for r in rows if r['condition']==c} for c in order.CONDITIONS}
    result={'model':model_key,'scope':scope,'source_split':'repeated-development internal_70_30/dev',
            'n_unique_questions':len({r['question_id'] for r in rows}),
            'n_unique_gold_documents':len({'PMID'+r['question_id'] for r in rows}),
            'classification_policy':'frozen v2 Stage B all rows including invalid; labels yes/no/maybe; absent-support class historical N/A',
            'human_reference':'v2 human dev26 B0 chunk IDs verified; 14 insufficient/12 sufficient; reviewer/time unknown; single reviewer; repeated dev',
            'semantic_audit':'mechanical only; citation legality and result-family rates do not establish semantic support',
            'per_condition':{},'paired':{},'cost':{}}
    failures=[]; pairs=[]
    for cond,items in by.items():
        rs=list(items.values())
        if not rs:continue
        pred=Counter(r.get('answerable') for r in rs)
        annotated=[r for r in rs if r['question_id'] in refs]
        ins=[r for r in annotated if refs[r['question_id']]['evidence_sufficiency']=='不足']
        suf=[r for r in annotated if refs[r['question_id']]['evidence_sufficiency']=='充分']
        # Same evidence set in reordered conditions: reference is about sufficiency of the content.
        for r in annotated:assert set(r['chunk_order'])==set(refs[r['question_id']]['verified_B0_chunk_ids'])
        withcit=[r for r in rs if r.get('citations')]
        per={'classification':classification(rs),'v1_compatibility':classification(rs,'v1'),
            'predicted_label_distribution':dict(Counter(r.get('label') for r in rs)),
            'parse_failure':ratio(sum(r.get('parsed_status',r['status'])=='invalid' for r in rs),len(rs)),
            'citation_out_of_range':ratio(sum(r.get('parsed_status',r['status'])=='invalid_citation' for r in rs),len(rs)),
            'complete_contract_violation':ratio(sum(bool(strict_issues(r)) for r in rs),len(rs)),
            'complete_contract_issue_counts':dict(Counter(issue for r in rs for issue in strict_issues(r))),
            'citation_terminal_period_only':ratio(sum(any(
                re.search(r'^Citations:\s*(?:None|E\d+(?:\s*,\s*E\d+)*)\.$',line.strip(),re.IGNORECASE)
                for line in (r['raw_output'] or '').splitlines()) for r in rs),len(rs)),
            'abstention_behavior':ratio(pred['no'],len(rs)),
            'answerable_distribution':dict(pred),'generation_exceptions':sum(r['finish_reason']=='exception' for r in rs),
            'output_budget_hits':sum(r['output_budget_hit'] for r in rs),
            'human_coverage':ratio(len(annotated),len(rs)),
            'unsupported_answer':ratio(sum(r['status']=='ok' and r['answerable']=='yes' for r in ins),len(ins)),
            'wrong_abstention':ratio(sum(r['status']=='ok' and r['answerable']=='no' for r in suf),len(suf)),
            'valid_abstention_insufficient':ratio(sum(r['status']=='ok' and r['answerable']=='no' for r in ins),len(ins)),
            'valid_answer_sufficient':ratio(sum(r['status']=='ok' and r['answerable']=='yes' for r in suf),len(suf)),
            'human_subset_failures':{'insufficient':sum(r['status']!='ok' for r in ins),'sufficient':sum(r['status']!='ok' for r in suf)},
            'diagnostic_result_family_cited':ratio(sum(bool(set(r['citations'])&set(r['result_positions'])) for r in withcit),len(withcit)),
            'diagnostic_E1_cited':ratio(sum(1 in r['citations'] for r in withcit),len(withcit)),
            'citation_position_counts':dict(Counter(str(c) for r in rs for c in r['citations'])),
            'output_tokens':distribution([r['generated_tokens'] for r in rs]),
            'output_chars':distribution([len(r['raw_output'] or '') for r in rs]),
            'latency_seconds':distribution([r['item_seconds'] for r in rs]),
            'peak_allocated_gib':max(r['peak_allocated_gib'] for r in rs),
            'peak_reserved_gib':max(r['peak_reserved_gib'] for r in rs),
            'confusion':classification(rs,'v1')['confusion']}
        result['per_condition'][cond]=per
        for r in rs:
            issue=strict_issues(r)
            if issue or not correct(r):
                failures.append({'sample_id':r['sample_id'],'condition':cond,'raw_output':r['raw_output'],
                    'gold':r['gold'],'label':r['label'],'status':r['status'],'contract_issues':issue,
                    'finish_reason':r['finish_reason'],'cache_key':r['cache_key'],
                    'evidence_block':r['evidence_block']})
    for cond in order.CONDITIONS[1:]:
        ps=[]
        for qid,r in by[cond].items():
            if qid not in by[order.CONDITIONS[0]]:continue
            b=by[order.CONDITIONS[0]][qid]
            p={'question_id':qid,'condition':cond,'input_changed':b['rendered_prompt']!=r['rendered_prompt'],
               'label_changed':b['label']!=r['label'],'answerable_changed':b['answerable']!=r['answerable'],
               'actual_citation_set_changed':cited(b)!=cited(r),'display_citations_changed':b['citations']!=r['citations'],
               'raw_changed':b['raw_output']!=r['raw_output'],'base_correct':correct(b),'condition_correct':correct(r),
               'label_transition':f"{b['label']}->{r['label']}",
               'base_result_positions':b['result_positions'],'base_cited_chunks':sorted(cited(b)),
               'condition_cited_chunks':sorted(cited(r))}
            ps.append(p);pairs.append(p)
        def aggregate(sub):
            b=sum(p['base_correct'] and not p['condition_correct'] for p in sub)
            c=sum(not p['base_correct'] and p['condition_correct'] for p in sub)
            return {'n_pairs':len(sub),**{k:ratio(sum(p[k] for p in sub),len(sub)) for k in
                ['label_changed','answerable_changed','actual_citation_set_changed','display_citations_changed','raw_changed']},
                'label_transitions':dict(Counter(p['label_transition'] for p in sub)),
                'mcnemar_correct_incorrect_only':v2score.mcnemar_exact(b,c)}
        result['paired'][cond]={'all':aggregate(ps), 'input_changed':aggregate([p for p in ps if p['input_changed']]),
                                'input_unchanged':aggregate([p for p in ps if not p['input_changed']])}
    result['cost']={'requests':len(rows),'fresh_this_execution':sum(not r['cache_hit'] for r in rows),
        'total_generated_tokens':sum(r['generated_tokens'] for r in rows),
        'generation_seconds_all_unique':sum(r['item_seconds'] for r in rows),
        'peak_allocated_gib':max(r['peak_allocated_gib'] for r in rows),
        'peak_reserved_gib':max(r['peak_reserved_gib'] for r in rows)}
    write_json(run_dir/'analysis.json',result)
    write_jsonl(run_dir/'pairs.jsonl',pairs)
    write_jsonl(run_dir/'failure_cases.jsonl',failures)
    print(model_key,scope,result['cost'],flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--scope',default='dev151');a=p.parse_args()
    analyze(a.model,a.scope)
