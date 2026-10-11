"""Validate and lock independent AI opinions before joining anonymous mappings."""
from collections import Counter
from datetime import datetime, timezone
from common import *
import argparse

def run(folder=None):
    folder=ROOT/'ai_assisted' if folder is None else (ROOT/folder).resolve()
    assert folder.is_relative_to(ROOT/'ai_assisted')
    path=folder/'ratings_blinded.json'
    audit=read_json(path); cases={c['audit_id']:c for c in read_json(folder/'blind_cases.json')}
    ratings=audit['ratings']
    assert audit['metadata']['review_locked'] and not audit['metadata']['human_ground_truth']
    assert len(ratings)==len(cases)==8 and {r['audit_id'] for r in ratings}==set(cases)
    locations=[]
    for r in ratings:
        evid={e['display']:e for e in cases[r['audit_id']]['evidence']}
        for loc in r['evidence_locations']:
            e=evid[loc['display']]
            assert loc['anonymous_chunk']==e['anonymous_chunk']
            assert e['text'][loc['char_start_zero_based']:loc['char_end_exclusive']]==loc['quote'],loc
            locations.append(loc)
    sha=digest(path)
    path.chmod(0o444)
    timestamp_key=next(k for k in ('timestamp_utc','reviewed_at_utc') if k in audit['metadata'])
    write_json(folder/'audit_lock.json',{'sha256':sha,'agent_self_lock_timestamp':audit['metadata'][timestamp_key],
        'agent_timestamp_source_field':timestamp_key,
        'filesystem_lock_timestamp':datetime.now(timezone.utc).isoformat(),'validated_cases':len(ratings),
        'validated_quote_locations':len(locations),'read_only':not bool(path.stat().st_mode & 0o200),
        'note':'Independent agent self-locked judgements before root technical validation and mapping inspection; no judgement edits.'})
    mapping={r['audit_id']:r for r in read_json(folder/'backend_mapping_locked.json')}
    joined=[{**r,'backend':mapping[r['audit_id']]} for r in ratings]
    fields=['evidence_sufficiency','evidence_supports_reason','reason_supports_label',
            'citation_traceability','citation_support','abstention_appropriateness']
    summary={'review_kind':'ai_assisted','human_ground_truth':False,'rating_sha256':sha,
        'scope':'Illustrative first two sorted smoke questions, four conditions, '+','.join(sorted({r['model'] for r in mapping.values()}))+'; selection not based on outputs. No prevalence claim.',
        'metadata':audit['metadata'],'counts':{f:dict(Counter(r[f] for r in ratings)) for f in fields},
        'by_question':{q:{r['backend']['condition']:{f:r[f] for f in fields} for r in joined if r['backend']['question_id']==q}
                       for q in sorted({r['backend']['question_id'] for r in joined})},
        'limitations':['AI opinions are not independent human truth','Model runtime identifier unavailable',
                      'N_A/unknown not counted as passing','Does not infer internal reasoning from Reason text']}
    write_json(folder/'ratings_unsealed.json',joined)
    write_json(folder/'summary.json',summary)
    assert digest(path)==sha
    print('AI assisted locked:',len(ratings),'cases,',len(locations),'quote locations; SHA',sha)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder');a=p.parse_args();run(a.folder)
