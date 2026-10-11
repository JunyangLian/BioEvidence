"""Reuse byte-identical historical tokenizer assets; validate fixed-revision Git/LFS IDs."""
import shutil
from fetch_model import DEST, fetch
from common import *

def run():
    names={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','merges.txt','vocab.json','model.safetensors.index.json','README.md','LICENSE'}
    meta=read_json(DEST/'repo_api.json'); records=[]
    for f in meta['files']:
        if f['path'] not in names:continue
        target=DEST/f['path'];old=V1/'artifacts/models/Qwen3-0.6B'/f['path']
        def matches(p):
            if not p.exists() or p.stat().st_size!=f['size']:return False
            if f.get('lfs'):return digest(p)==f['lfs']['oid']
            return hashlib.sha1(f"blob {f['size']}\0".encode()+p.read_bytes()).hexdigest()==f['oid']
        if matches(target):source='already verified local asset'
        elif matches(old):shutil.copyfile(old,target);source=str(old)
        else:fetch(f['path'],endpoint='https://hf-mirror.com');source='fixed revision mirror; official Git/LFS identity checked'
        assert matches(target)
        records.append({'file':f['path'],'source':source,'sha256':digest(target),'official_content_identity_verified':True})
    write_json(ROOT/'reports/model_assets.json',{'revision':meta['revision'],'assets':records,'historical_sources_read_only':True})
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(str(DEST),local_files_only=True)
    rows=[]
    for doc in jsonl(ROOT/'data/dev151_conditions.jsonl'):
        prompt=tok.apply_chat_template(doc['messages'],tokenize=False,add_generation_prompt=True)
        ids=tok(prompt,add_special_tokens=False)['input_ids']
        assert prompt.count(tb.SYSTEM_PROMPT)==1 and doc['evidence_block'] in prompt
        assert prompt.endswith('<|im_start|>assistant\n') and '<think>' not in prompt
        assert len(ids)+160<=2048
        rows.append({'sample_id':doc['sample_id'],'question_id':doc['question_id'],'condition':doc['condition'],
                     'rendered_prompt':prompt,'input_token_ids':ids,'input_tokens':len(ids),
                     'template_sha256':fingerprint(tok.chat_template),'evidence_block_sha8':doc['block_sha8']})
    write_jsonl(ROOT/'data/instruct4b_preflight_rendered.jsonl',rows)
    write_json(ROOT/'reports/instruct4b_input_preflight.json',{'passed':True,'rows':len(rows),
        'min_input_tokens':min(r['input_tokens'] for r in rows),'max_input_tokens':max(r['input_tokens'] for r in rows),
        'model_calls':0,'weights_not_required':True,'non_thinking_template_verified':True,
        'system_once_and_evidence_exact':True,'no_context_truncation':True})
    print('4B asset identities and 604 actual input templates passed, no model calls')

if __name__=='__main__':run()
