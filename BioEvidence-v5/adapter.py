"""Task B generation adapter: parsing and scoring delegate to frozen code."""
from common import tb, classification
RUNTIME = {}

def score_one(doc, raw):
    parsed = tb.parse_output(raw, n_evidence=len(doc['chunk_order'])).to_dict()
    meta = RUNTIME.get((doc['question_id'], doc.get('condition')),{})
    status = 'invalid' if meta.get('generation_error') else parsed['status']
    return {**doc, 'raw_output': raw, **parsed, 'parsed_status': parsed['status'], 'status': status,
            'error_codes': ([parsed['status']] if parsed['status'] != 'ok' else []) + parsed['citation_issues'] +
                           ([meta['generation_error']] if meta.get('generation_error') else [])}

def process_results(doc, results):
    if len(results) != 1:
        raise ValueError('Task B requires exactly one untouched raw completion')
    row = score_one(doc, results[0])
    return {'bio_accuracy': row, 'bio_macro_f1': row, 'bio_invalid_rate': row}

def agg_accuracy(rows):
    return classification(rows)['accuracy']

def agg_f1(rows):
    return classification(rows)['macro_f1']

def agg_invalid(rows):
    return sum(r['status'] != 'ok' for r in rows) / len(rows) if rows else None

def make_task(docs, max_new_tokens=160, name='bioevidence_taskb'):
    from datasets import Dataset, DatasetDict
    from lm_eval.api.task import ConfigurableTask
    def data(**kwargs):
        return DatasetDict({'dev': Dataset.from_list(docs)})
    return ConfigurableTask(config={
        'task': name, 'dataset_path': 'json', 'custom_dataset': data,
        'validation_split': 'dev', 'output_type': 'generate_until',
        'doc_to_text': lambda doc: doc['rendered_prompt'], 'doc_to_target': lambda doc: doc['gold'],
        'process_results': process_results, 'num_fewshot': 0,
        'generation_kwargs': {'until': [], 'max_gen_toks': max_new_tokens, 'do_sample': False,
                              'num_beams': 1},
        'metric_list': [
            {'metric': 'bio_accuracy', 'aggregation': agg_accuracy, 'higher_is_better': True},
            {'metric': 'bio_macro_f1', 'aggregation': agg_f1, 'higher_is_better': True},
            {'metric': 'bio_invalid_rate', 'aggregation': agg_invalid, 'higher_is_better': False}],
        'metadata': {'version': 'v4.1', 'source_split': 'internal_70_30/dev',
                     'scorer': 'frozen v2_stageb_dev_analysis.metrics'}})
