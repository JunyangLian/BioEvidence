"""Fixed historical-target QLoRA; complete samples and actual loss masks audited."""
from common import *
import argparse,time,traceback,math
from datetime import datetime,timezone

def run(stage):
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig,TrainerCallback,set_seed
    from datasets import Dataset
    from peft import LoraConfig
    from trl import SFTConfig,SFTTrainer
    protocol=read_json(ROOT/'config/protocol.json');t=protocol['training']
    rows=jsonl(ROOT/'data/training_native4b.jsonl');assert len(rows)==582
    assert digest(ROOT/'data/sft_taskb_exact.jsonl')==protocol['training_data_sha256']
    assert max(r['total_tokens'] for r in rows)<=t['max_length']
    model_path=(ROOT/read_json(ROOT/'config/models.json')['tuned_4b']['path']).resolve()
    set_seed(t['seed']);torch.set_num_threads(8)
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    if tok.pad_token is None:tok.pad_token=tok.eos_token
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
    model=AutoModelForCausalLM.from_pretrained(str(model_path),quantization_config=quant,device_map={'':0},local_files_only=True)
    model.config.use_cache=False
    folder=ROOT/'runs/training'/stage;folder.mkdir(parents=True,exist_ok=True)
    ds=Dataset.from_list([{'prompt':r['prompt'],'completion':r['completion']} for r in rows])
    cfg=SFTConfig(output_dir=str(folder/'checkpoints'),per_device_train_batch_size=1,
        gradient_accumulation_steps=1 if stage=='smoke' else t['gradient_accumulation_steps'],
        num_train_epochs=t['num_train_epochs'],max_steps=2 if stage=='smoke' else -1,
        learning_rate=t['learning_rate'],lr_scheduler_type=t['lr_scheduler_type'],optim=t['optim'],
        max_length=t['max_length'],packing=False,completion_only_loss=True,
        bf16=True,fp16=False,gradient_checkpointing=True,gradient_checkpointing_kwargs={'use_reentrant':False},
        seed=t['seed'],data_seed=t['data_seed'],logging_steps=1,report_to=[],
        save_strategy='no' if stage=='smoke' else 'steps',save_steps=25,save_total_limit=2,
        do_train=True,dataloader_num_workers=0)
    peft=LoraConfig(r=t['lora_r'],lora_alpha=t['lora_alpha'],lora_dropout=t['lora_dropout'],bias='none',
        task_type='CAUSAL_LM',target_modules=t['target_modules'])
    trainer=SFTTrainer(model=model,args=cfg,train_dataset=ds,processing_class=tok,peft_config=peft)
    audited=[]
    for i,r in enumerate(rows):
        prepared=trainer.train_dataset[i]
        batch=trainer.data_collator([prepared])
        ids=batch['input_ids'][0].tolist();labels=batch['labels'][0].tolist()
        # Frozen E7 used this same TRL version: it appends EOS after the native
        # trailing newline. Explicitly verify this documented trainer behavior.
        completion=r['completion'] if r['completion'].endswith(tok.eos_token) else r['completion']+tok.eos_token
        expected_ids=tok(r['prompt']+completion,add_special_tokens=False)['input_ids']
        assert expected_ids[:r['total_tokens']]==r['input_ids'] and len(expected_ids)<=t['max_length']
        assert ids==expected_ids,('Trainer changed complete input',i,len(ids),r['total_tokens'])
        prefix=r['prompt_tokens'];assert all(x==-100 for x in labels[:prefix]),('Prompt trained',i)
        assert labels[prefix:]==ids[prefix:],('Completion masked or rewritten',i)
        audited.append({'record_index':i,'question_id':r['question_id'],'input_token_ids':ids,'labels':labels,
                        'masked_tokens':prefix,'supervised_tokens':len(ids)-prefix,
                        'trl_appended_eos_tokens':len(ids)-r['total_tokens'],'passed':True})
    write_jsonl(folder/'loss_masks.jsonl',audited)
    short=min(range(len(rows)),key=lambda i:rows[i]['total_tokens']);long=max(range(len(rows)),key=lambda i:rows[i]['total_tokens'])
    if stage=='smoke':trainer.train_dataset=trainer.train_dataset.select([short,long])
    else:assert read_json(ROOT/'runs/training/smoke/report.json')['passed'],'Real longest-sample optimizer smoke required'
    trainable=sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    # Every step records finite loss/gradient and adapter update, not a load-only smoke.
    tracked=next(p for n,p in trainer.model.named_parameters() if p.requires_grad and 'lora_B' in n)
    before=tracked.detach().float().cpu().clone();steps=[];started=time.perf_counter()
    class Audit(TrainerCallback):
        def on_log(self,args,state,control,logs=None,**kwargs):
            logs=logs or {}
            for k in ('loss','grad_norm'):
                if k in logs:assert math.isfinite(float(logs[k])),(k,logs[k])
            rec={'global_step':state.global_step,'elapsed_seconds':time.perf_counter()-started,**logs,
                'peak_allocated_gib':torch.cuda.max_memory_allocated()/1024**3,
                'peak_reserved_gib':torch.cuda.max_memory_reserved()/1024**3}
            steps.append(rec)
            with (folder/'steps.jsonl').open('a',encoding='utf-8') as f:f.write(__import__('json').dumps(rec)+'\n')
            if rec['elapsed_seconds']>protocol['expansion']['training_wall_budget_seconds']:
                raise RuntimeError('Preregistered training wall budget exceeded; preserve checkpoints')
    trainer.add_callback(Audit());torch.cuda.reset_peak_memory_stats()
    from transformers.trainer_utils import get_last_checkpoint
    checkpoint=get_last_checkpoint(str(folder/'checkpoints')) if stage=='full' and (folder/'checkpoints').exists() else None
    result=trainer.train(resume_from_checkpoint=checkpoint)
    changed=not torch.equal(before,tracked.detach().float().cpu())
    assert changed,'Adapter did not update'
    expected=2 if stage=='smoke' else math.ceil(582/8)*3
    assert result.global_step==expected,(result.global_step,expected)
    adapter_dir=ROOT/'artifacts/adapters/qwen3-4b-e7-target' if stage=='full' else folder/'smoke_adapter'
    trainer.save_model(str(adapter_dir))
    report={'passed':True,'stage':stage,'global_step':result.global_step,'training_loss':result.training_loss,
        'train_seconds':time.perf_counter()-started,'trainable_parameters':trainable,'adapter_updated':changed,
        'n_mask_checks':len(audited),'shortest_record':short,'longest_record':long,
        'longest_tokens':rows[long]['total_tokens'],'no_input_truncation':True,
        'protocol_sha256':digest(ROOT/'config/protocol.json'),'model_path':str(model_path),
        'adapter_dir':str(adapter_dir),'adapter_hashes':{p.name:digest(p) for p in adapter_dir.iterdir() if p.is_file()},
        'checkpoint_selection':'fixed final three epochs; operational resume only; no dev selection',
        'effective_sft_config':cfg.to_dict(),'peak_allocated_gib':torch.cuda.max_memory_allocated()/1024**3,
        'peak_reserved_gib':torch.cuda.max_memory_reserved()/1024**3,
        'estimated_full_seconds_from_smoke':(time.perf_counter()-started)/2*582*3 if stage=='smoke' else None,
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'steps':steps}
    write_json(folder/'report.json',report);print('TRAINING PASSED',stage,result.global_step,report['train_seconds'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['smoke','full']);a=p.parse_args()
    try:run(a.stage)
    except Exception:
        err=traceback.format_exc();write_json(ROOT/f'runs/training/{a.stage}/failure_{int(time.time())}.json',{'error':err})
        print(err,flush=True);raise
