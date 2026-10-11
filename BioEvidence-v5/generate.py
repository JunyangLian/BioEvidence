"""HFLM generation via actual harness tasks, with per-request resume/audit."""
import argparse
import time
import traceback
import importlib.metadata
from datetime import datetime, timezone
from common import *
import adapter

def run(model_key, n=10, regression=False, conditions=None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    from lm_eval.models.huggingface import HFLM
    from lm_eval import evaluator
    parity=read_json(ROOT/'reports/scoring_parity.json')
    assert parity['passed'],'Real offline scoring parity is required before new generation'
    configs=read_json(ROOT/'config/models.json'); cfg=configs[model_key]; shared=configs['shared']
    model_path=(ROOT/cfg['path']).resolve()
    adapter_path=(ROOT/cfg['adapter']).resolve() if cfg['adapter'] else None
    identity={p.name:digest(p) for p in model_path.iterdir() if p.is_file() and
        (p.suffix in ('.json','.safetensors','.txt','.jinja') and p.name not in ('download_manifest.json','repo_api.json','hf_model_info.json'))}
    if adapter_path:
        identity['adapter']={p.name:digest(p) for p in adapter_path.iterdir() if p.is_file()}
    versions={p:importlib.metadata.version(p) for p in ('lm_eval','transformers','torch','bitsandbytes','peft','datasets','accelerate')}
    config_fingerprint=fingerprint({'model':cfg,'shared':shared,'identity':identity,'packages':versions,
        'template':tb.template_fingerprint(),'adapter_code':digest(ROOT/'adapter.py'),
        'runner_code':digest(ROOT/'generate.py'),'common_code':digest(ROOT/'common.py'),
        'historical_parser':digest(V1/'src/bioevidence/inference/prompts_taskb.py'),
        'historical_scorer':digest(V2/'scripts/v2_stageb_dev_analysis.py')})
    torch.manual_seed(shared['seed'])
    torch.cuda.reset_peak_memory_stats()
    started=time.perf_counter()
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    if tok.pad_token is None: tok.pad_token=tok.eos_token
    quant=BitsAndBytesConfig(**{**shared['quantization'],'bnb_4bit_compute_dtype':torch.bfloat16})
    base=AutoModelForCausalLM.from_pretrained(str(model_path),quantization_config=quant,
        device_map={'':0},local_files_only=True)
    model=PeftModel.from_pretrained(base,str(adapter_path),local_files_only=True) if adapter_path else base
    model.eval()
    load_seconds=time.perf_counter()-started
    all_docs=jsonl(ROOT/'data/dev151_conditions.jsonl')
    selected_ids=sorted({d['question_id'] for d in all_docs})[:n]
    docs=[d for d in all_docs if d['question_id'] in selected_ids and
          (not conditions or d['condition'] in conditions)]
    for d in docs:
        kwargs={'enable_thinking':False} if cfg['thinking'] is False else {}
        d['rendered_prompt']=tok.apply_chat_template(d['messages'],tokenize=False,add_generation_prompt=True,**kwargs)
        d['input_token_ids']=tok(d['rendered_prompt'],add_special_tokens=False)['input_ids']
        d['input_tokens']=len(d['input_token_ids'])
        assert d['input_tokens']+shared['max_new_tokens']<=shared['max_length'], 'Context overflow: do not truncate evidence'
        assert d['rendered_prompt'].count(tb.SYSTEM_PROMPT)==1,'System instruction missing/duplicated'
        assert d['evidence_block'] in d['rendered_prompt']
        d['config_fingerprint']=config_fingerprint
    write_json(ROOT/f'runs/{model_key}/config.json',{'configuration':cfg,'shared':shared,'identity':identity,
        'weight_source':read_json(model_path/'download_manifest.json') if (model_path/'download_manifest.json').exists() else None,
        'packages':versions,'config_fingerprint':config_fingerprint,'model_load_seconds':load_seconds,
        'chat_template':tok.chat_template,'chat_template_sha256':fingerprint(tok.chat_template),
        'input_tokens_min':min(d['input_tokens'] for d in docs),'input_tokens_max':max(d['input_tokens'] for d in docs),
        'selected_ids':selected_ids,'timestamp_utc':datetime.now(timezone.utc).isoformat()})
    records={}; cache_dir=ROOT/'cache/generation'/model_key/config_fingerprint
    class AuditHF(HFLM):
        def _model_generate(self, context, max_length, stop, **kwargs):
            # Guard against harness's automatic context truncation.
            assert context.shape[-1]==self.expected_tokens,'HF tokenization/context mismatch'
            assert context[0].tolist()==self.expected_ids,'HF tokenizer changed rendered input tokens'
            out=super()._model_generate(context,max_length,stop,**kwargs)
            self.last_ids=out[0][context.shape[-1]:].tolist()
            self.actual_stop=stop
            return out
        def generate_until(self, requests, disable_tqdm=False):
            outputs=[]
            for request in requests:
                d=dict(request.doc)
                key=fingerprint({'config':config_fingerprint,'condition':d['condition'],
                    'sample_id':d['sample_id'],'prompt':d['rendered_prompt'],'request_kwargs':request.args[1]})
                cache=cache_dir/(key+'.json')
                if cache.exists():
                    rec=read_json(cache)
                    if rec.get('finish_reason') == 'exception':
                        cache=None # failed request may resume; no silent retry within a run
                    else:
                        rec['cache_hit']=True
                        records[(d['question_id'],d['condition'])]=rec
                        adapter.RUNTIME[(d['question_id'],d['condition'])]=rec
                        outputs.append(rec['raw_output']); continue
                torch.cuda.reset_peak_memory_stats()
                t0=time.perf_counter(); self.last_ids=[]; self.expected_tokens=d['input_tokens']; self.expected_ids=d['input_token_ids']
                try:
                    raw=super().generate_until([request],disable_tqdm=True)[0]
                    torch.cuda.synchronize()
                    eos=model.generation_config.eos_token_id
                    eos_set=set(eos if isinstance(eos,list) else [eos])
                    hit_eos=bool(self.last_ids and self.last_ids[-1] in eos_set)
                    reached_budget=len(self.last_ids)>=shared['max_new_tokens'] and not hit_eos
                    error='output_budget_exhausted_without_eos' if reached_budget else None
                    stopped='eos' if hit_eos else 'length' if reached_budget else 'stop_sequence'
                except Exception as exc:
                    raw=None; error=f'{type(exc).__name__}: {exc}'; stopped='exception'; reached_budget=False
                rec={**d,'raw_output':raw,'cache_key':key,'cache_hit':False,
                     'generated_token_ids':self.last_ids,'generated_tokens':len(self.last_ids),
                     'generation_error':error,'finish_reason':stopped,'output_budget_hit':reached_budget,
                     'item_seconds':time.perf_counter()-t0,
                     'peak_allocated_gib':torch.cuda.max_memory_allocated()/1024**3,
                     'peak_reserved_gib':torch.cuda.max_memory_reserved()/1024**3,
                     'stop_sequences':getattr(self,'actual_stop',None),
                     'raw_with_special_tokens':tok.decode(self.last_ids,skip_special_tokens=False),
                     'timestamp_utc':datetime.now(timezone.utc).isoformat()}
                adapter.RUNTIME[(d['question_id'],d['condition'])]=rec
                scored=adapter.score_one(d,raw)
                rec.update({k:scored[k] for k in ('status','label','reason','answerable','citations','parse_note',
                    'citation_issues','error_codes','parsed_status')})
                if regression and model_key=='e7_06b':
                    inputs=tok(d['rendered_prompt'],return_tensors='pt').to('cuda')
                    with torch.no_grad(): direct=model.generate(**inputs,max_new_tokens=160,do_sample=False,num_beams=1)
                    direct_raw=tok.decode(direct[0][inputs['input_ids'].shape[-1]:],skip_special_tokens=True)
                    rec['direct_transformers_regression']={'raw_output':direct_raw,'equal_to_harness':direct_raw==raw,
                        'tokenization_equal':inputs['input_ids'][0].tolist()==d['input_token_ids'],
                        'parsed':tb.parse_output(direct_raw,len(d['chunk_order'])).to_dict()}
                write_json(cache_dir/(key+'.json'),rec)
                records[(d['question_id'],d['condition'])]=rec
                outputs.append(raw or '')
                print(model_key,len(records),'/',len(docs),d['question_id'],d['condition'],rec['status'],
                      rec['generated_tokens'],round(rec['item_seconds'],2),'s',flush=True)
            return outputs
    lm=AuditHF(pretrained=model,tokenizer=tok,batch_size=1,max_length=shared['max_length'],
               device='cuda',add_bos_token=False)
    task=adapter.make_task(docs,shared['max_new_tokens'])
    results=evaluator.simple_evaluate(model=lm,tasks=[task],num_fewshot=0,bootstrap_iters=0,
        log_samples=True,apply_chat_template=False,random_seed=shared['seed'],
        numpy_random_seed=shared['seed'],torch_random_seed=shared['seed'])
    run_dir=ROOT/'runs'/model_key/(('B0_dev151' if conditions else 'dev151') if n==151 else 'smoke10')
    write_json(run_dir/'harness_results.json',results)
    write_jsonl(run_dir/'predictions.jsonl',sorted(records.values(),key=lambda r:(r['question_id'],r['condition'])))
    summary={'model':model_key,'n':len(records),'n_samples':len(selected_ids),'elapsed_seconds':time.perf_counter()-started,
        'model_load_seconds':load_seconds,'fresh_requests':sum(not r['cache_hit'] for r in records.values()),
        'cache_hits':sum(r['cache_hit'] for r in records.values()),'config_fingerprint':config_fingerprint,
        'generation_exceptions':sum(r['finish_reason']=='exception' for r in records.values()),
        'output_budget_hits':sum(r['output_budget_hit'] for r in records.values()),
        'harness_results':results['results'],'input_system_and_context_checks_passed':True,
        'direct_regression': [r.get('direct_transformers_regression') for r in records.values() if 'direct_transformers_regression' in r]}
    write_json(run_dir/'summary.json',summary)
    print(summary,flush=True)
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--model',choices=['base_06b','instruct_4b','e7_06b','tuned_4b'],required=True)
    ap.add_argument('--n',type=int,default=10); ap.add_argument('--regression',action='store_true'); ap.add_argument('--b0-only',action='store_true'); a=ap.parse_args()
    try: run(a.model,a.n,a.regression,['B0_original'] if a.b0_only else None)
    except Exception:
        error=traceback.format_exc(); print(error,flush=True)
        write_json(ROOT/f'runs/{a.model}/failed_attempt_{int(time.time())}.json',{'error':error,'n':a.n})
        raise
