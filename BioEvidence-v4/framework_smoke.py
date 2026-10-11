"""Five official-task samples, or clearly labeled synthetic generation fallback."""
import traceback
from common import *

def run():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from lm_eval.models.huggingface import HFLM
    from lm_eval import evaluator
    from adapter import make_task
    path=str(V1/'artifacts/models/Qwen3-0.6B')
    tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,device_map={'':0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16))
    lm=HFLM(pretrained=model,tokenizer=tok,batch_size=1,max_length=2048,device='cuda',add_bos_token=False)
    try:
        result=evaluator.simple_evaluate(model=lm,tasks=['arc_easy'],limit=5,num_fewshot=0,
            bootstrap_iters=0,log_samples=True)
        kind='official arc_easy five samples; framework connectivity only'
    except Exception:
        write_json(ROOT/'runs/framework_smoke/official_task_failure.json',{'traceback':traceback.format_exc()})
        docs=[]
        for i in range(5):
            text=f'Synthetic interface check {i+1}. Reply in four lines: Label: yes, Reason: test., Citations: E1, Answerable: yes.'
            prompt=tok.apply_chat_template([{'role':'user','content':text}],tokenize=False,
                add_generation_prompt=True,enable_thinking=False)
            docs.append({'question_id':'synthetic-'+str(i),'condition':'synthetic','gold':'yes',
                         'chunk_order':['synthetic-chunk'],'rendered_prompt':prompt})
        result=evaluator.simple_evaluate(model=lm,tasks=[make_task(docs,name='synthetic_framework_only')],
            num_fewshot=0,bootstrap_iters=0,log_samples=True)
        kind='SYNTHETIC interface fallback; no real data parity or model capability claim'
    write_json(ROOT/'runs/framework_smoke/results.json',{'kind':kind,'results':result,
        'peak_allocated_gib':torch.cuda.max_memory_allocated()/1024**3})
    print(kind,flush=True)

if __name__=='__main__':run()
