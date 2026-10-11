"""Exact historical training records, native templates, and immutable V5 protocol."""
from datetime import datetime,timezone
from collections import Counter
from common import *
def run():
    from transformers import AutoTokenizer
    protocol_path=ROOT/'config/protocol.json'
    protocol={'version':'v5_historical_target_anchor_v1','timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'question':'Within each starting model, what changes after domain adaptation under the historical E7 supervision?',
        'data_source':str(V1/'data/processed/pubmedqa/sft_taskb.jsonl'),'training_records':582,
        'training_data_sha256':digest(V1/'data/processed/pubmedqa/sft_taskb.jsonl'),
        'no_target_cleaning':True,'no_order_augmentation':True,'no_dev_checkpoint_selection':True,
        'checkpoint':'Final fixed 3-epoch checkpoint, not best dev checkpoint','validation_split':None,
        'training':{'max_length':1024,'num_train_epochs':3,'per_device_train_batch_size':1,'gradient_accumulation_steps':8,
            'learning_rate':1e-4,'lr_scheduler_type':'linear','optim':'paged_adamw_8bit','seed':20260918,'data_seed':20260918,
            'bf16':True,'fp16':False,'packing':False,'completion_only_loss':True,'gradient_checkpointing':True,
            'gradient_checkpointing_kwargs':{'use_reentrant':False},'lora_r':8,'lora_alpha':16,'lora_dropout':.05,
            'target_modules':['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']},
        'smoke':{'records':'shortest and longest complete native-rendered records','optimizer_steps':2,
            'must_check_forward_backward_optimizer':True,'smoke_adapter_not_reused_for_training':True,
            'finite_retry':'At most one evidence-based memory optimization; never shorten evidence or change targets silently'},
        'expansion':{'primary_B0':604,'complete_four_condition_rows':2416,'preexisting_V4_raw_rows':1208,
            'E7_historical_rows_available':604,'expected_new_main_generations_if_reuse_passes':604,
            'gate':'Input/weight/parser integrity, technical feasibility and declared resource budget, never favorable scores',
            'generation_budget_seconds':7200,'training_wall_budget_seconds':21600,
            'no_new_success_threshold':True},
        'limits':['Repeated dev151; no fresh holdout','E7 legacy labels retain known proxy limitations',
            'No pure parameter-size effect','No pure position effect: order + renumbering',
            'Single training seed; no claim of seed robustness','Existing E7 saw all 582; do not carve a pseudo-independent validation set from them']}
    if protocol_path.exists():
        old=read_json(protocol_path);protocol['timestamp_utc']=old['timestamp_utc'];assert protocol==old
    else:write_json(protocol_path,protocol);protocol_path.chmod(0o444)
    models=read_json(V4/'config/models.json');models['instruct_4b']['path']='../BioEvidence-v4/models/Qwen3-4B-Instruct-2507'
    models['e7_06b']['role']='main tuned historical E7 comparison; not v2 C1 old-target'
    models['tuned_4b']={**models['instruct_4b'],'adapter':'artifacts/adapters/qwen3-4b-e7-target','role':'main V5 domain adaptation'}
    write_json(ROOT/'config/models.json',models)
    for name in ('dev151_conditions.jsonl','human_dev26_reference.json'):
        (ROOT/'data').mkdir(exist_ok=True);(ROOT/'data'/name).write_bytes((V4/'data'/name).read_bytes())
    rows=jsonl(V1/'data/processed/pubmedqa/sft_taskb.jsonl');assert len(rows)==582
    ids={r['question_id'] for r in rows}
    splits=jsonl(V1/'data/manifests/split_pubmedqa_pqal_v1.jsonl')
    train={r['question_id'] for r in splits if r['scheme']=='internal_70_30' and r['split']=='train'}
    dev={d['question_id'] for d in jsonl(ROOT/'data/dev151_conditions.jsonl')}
    assert ids<=train and not ids&dev,'Training/dev question overlap'
    assert all(r['template_version']==tb.TEMPLATE_VERSION and r['messages'][0]['content']==tb.SYSTEM_PROMPT for r in rows)
    tok=AutoTokenizer.from_pretrained(str(V4/'models/Qwen3-4B-Instruct-2507'),local_files_only=True)
    encoded=[]
    for index,r in enumerate(rows):
        rendered=tok.apply_chat_template(r['messages'],tokenize=False,add_generation_prompt=False)
        marker='<|im_start|>assistant\n';cut=rendered.rfind(marker)+len(marker);assert cut>=len(marker)
        prompt,completion=rendered[:cut],rendered[cut:]
        assert completion.startswith(r['messages'][-1]['content']) and rendered.count(tb.SYSTEM_PROMPT)==1
        ids_full=tok(rendered,add_special_tokens=False)['input_ids'];ids_prompt=tok(prompt,add_special_tokens=False)['input_ids']
        assert ids_full[:len(ids_prompt)]==ids_prompt and len(ids_full)<=1024,'Never truncate complete training evidence/target'
        encoded.append({'record_index':index,'question_id':r['question_id'],'sample_type':r['sample_type'],
            'messages':r['messages'],'prompt':prompt,'completion':completion,'input_ids':ids_full,
            'prompt_tokens':len(ids_prompt),'total_tokens':len(ids_full),'completion_tokens':len(ids_full)-len(ids_prompt),
            'record_fingerprint':fingerprint(r),'source':str(V1/'data/processed/pubmedqa/sft_taskb.jsonl')})
    write_jsonl(ROOT/'data/training_native4b.jsonl',encoded)
    (ROOT/'data/sft_taskb_exact.jsonl').write_bytes((V1/'data/processed/pubmedqa/sft_taskb.jsonl').read_bytes())
    chunks={r['chunk_id']:r for r in jsonl(V1/'data/processed/pubmedqa/corpus_chunks.jsonl')}
    no_results=sum(not any('RESULT' in chunks[c]['section'].upper() or 'FINDING' in chunks[c]['section'].upper()
        for c in r['evidence_meta']['used_chunk_ids']) for r in rows if r['gold_answerable']=='yes')
    write_json(ROOT/'reports/training_data_audit.json',{'passed':True,'n_records':582,'n_unique_questions':len(ids),
        'gold_answerable_counts':dict(Counter(r['gold_answerable'] for r in rows)),
        'no_result_family_in_answerable_yes':no_results,'interpretation':'Structural flag only; not automatic insufficiency or wrong target',
        'native4b_min_tokens':min(r['total_tokens'] for r in encoded),'native4b_max_tokens':max(r['total_tokens'] for r in encoded),
        'no_truncation':True,'train_dev_question_overlap':0,'taskb_messages_verified':True,
        'historical_metadata_discrepancy':'train_report header imported Task A identifier; actual data messages are frozen Task B. Historical artifacts unchanged.',
        'source_sha256':protocol['training_data_sha256'],'copied_source_sha256':digest(ROOT/'data/sft_taskb_exact.jsonl'),
        'native_template_sha256':fingerprint(tok.chat_template),'protocol_sha256':digest(protocol_path)})
    print('Exact training data audit passed: 582 records; native4B max',max(r['total_tokens'] for r in encoded),flush=True)
if __name__=='__main__':run()
