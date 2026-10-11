"""Read-only historical E7 training alignment, with remaining differences explicit."""
from common import *

def run():
    import yaml
    cfg_path=V1/'configs/train_taskb.yaml';cfg=yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
    old_path=V1/'runs/P6-taskb-20260920/train_report.json';old=read_json(old_path)
    new=read_json(ROOT/'runs/training/full/report.json');protocol=read_json(ROOT/'config/protocol.json')
    old_adapter=read_json(V1/'artifacts/adapters/p6-taskb-lora/adapter_config.json')
    new_adapter=read_json(Path(new['adapter_dir'])/'adapter_config.json')
    fields=['max_length','num_train_epochs','per_device_train_batch_size','gradient_accumulation_steps',
            'learning_rate','optim','seed','packing','completion_only_loss','bf16','fp16']
    pairs={k:{'historical_effective':old['sft_config_effective'][k],
        'new_effective':new['effective_sft_config'][k]} for k in fields}
    assert all(v['historical_effective']==v['new_effective'] for v in pairs.values())
    for k in ['r','lora_alpha','lora_dropout','bias','task_type']:
        pairs['lora_'+k]={'historical_adapter':old_adapter[k],'new_adapter':new_adapter[k]}
        assert old_adapter[k]==new_adapter[k]
    assert set(old_adapter['target_modules'])==set(new_adapter['target_modules'])
    assert old['n_records']==new['n_mask_checks']==582
    assert digest(V1/cfg['data']['path'])==protocol['training_data_sha256']
    versions=read_json(V1/'runs/P0-env-20260918/env_report.json')['packages']
    env=read_json(ROOT/'environment.json')['packages']
    packages={k:{'historical_P0_environment':versions[k],'V5_actual':env[k],
        'same_reported_version':versions[k]==env[k]} for k in ['torch','transformers','peft','trl','accelerate','datasets','bitsandbytes']}
    report={'passed':True,'source_paths':{'historical_config':str(cfg_path),'historical_train_report':str(old_path)},
        'source_sha256':{'historical_config':digest(cfg_path),'historical_train_report':digest(old_path)},
        'same_historical_582_target_file_sha256':protocol['training_data_sha256'],
        'actual_effective_parameters':pairs,'target_modules':sorted(old_adapter['target_modules']),
        'reported_package_versions':packages,
        'package_evidence_limit':'P0 environment report and adapter PEFT metadata, not an independently saved complete P6 installation manifest; no binary identity claim',
        'remaining_differences':[
            'Different model architecture, model version and instruction-training history',
            'Native chat templates/tokenization/lengths differ; 0.6B historical completion includes empty nonthinking header, 4B native has none',
            'Same LoRA rank/modules do not equalize trainable parameter count: historical E7 5046272 versus new 4B 16515072',
            'Historical save_strategy=no; V5 operational checkpoints every25 updates for recovery, never dev selection',
            'Full historical runtime source/binary snapshot not independently available; V5 actual environment is pinned',
            'E7 historical generation uses direct HF; V5 generation uses HFLM; migration verified on10 only'],
        'no_dev_checkpoint_selection':True,'no_pure_scale_or_equal_compute_inference':True}
    write_json(ROOT/'reports/E7_training_alignment.json',report)
    print('Historical E7 training parameters aligned; differences retained',flush=True)

if __name__=='__main__':run()
