"""Resolve PyPI attestations when available; preserve unavailable source commit."""
import urllib.request
from common import *

def run():
    install=read_json(ROOT/'install-snapshot-report.json')
    report={}
    for name in ('lm_eval','transformers'):
        entry=next(e for e in install['install'] if e['metadata']['name'].replace('-','_').lower()==name)
        file=entry['download_info']['url'].split('/')[-1]
        version=entry['metadata']['version']
        url=f'https://pypi.org/integrity/{name}/{version}/{file}/provenance'
        try:
            with urllib.request.urlopen(url,timeout=20) as r:data=json.load(r)
            write_json(ROOT/f'reports/{name}_pypi_attestations.json',data)
            report[name]={'package_version':version,'url':url,'attestations':data}
        except Exception as exc:
            report[name]={'package_version':version,'source_commit':None,'error':str(exc),
                          'fallback':'installed source SHA256 + official wheel archive SHA256'}
    write_json(ROOT/'reports/source_provenance.json',report)
    print({k:v.get('error','attestation saved') for k,v in report.items()},flush=True)

if __name__=='__main__':run()
