import json
from dataclasses import asdict

def audit_json(report):
    data = asdict(report)
    # La descarga de trazabilidad no duplica el texto completo de las evidencias.
    for evidence in data['evidence']:
        evidence['page_count'] = len(evidence.pop('pages'))
    data['version'] = '0.2.0'
    data['scope'] = 'Borrador revisable. Las asociaciones fueron indicadas por el usuario; no certifican cumplimiento.'
    return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
