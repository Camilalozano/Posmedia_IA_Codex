"""Orquesta la versión inicial; no realiza consultas automáticas a SECOP."""
import hashlib
from src.models import Field, Evidence, Report
from src.extraction.pdf_reader import pdf_text
from src.extraction.contract_fields import extract_contract
from src.extraction.obligations import extract_obligations
from src.processing.batch import expand_inputs

def prepare_report(process_number, contract, uploads):
    process_number = process_number.strip()
    if not process_number:
        raise ValueError('Indique el número de proceso.')
    fields = extract_contract([])
    obligations, warnings = [], []
    if contract:
        name, data = contract
        text, pages = pdf_text(data)
        fields = extract_contract(pages)
        for value in fields.values():
            if value.source.startswith('Página'):
                value.source = name + ' · ' + value.source
        for item in extract_obligations(text):
            body = item['obligaciones_especificas']
            obligations.append(Field(str(item['numero_obligacion']) + '. ' + body,
                                     name + ' · sección obligaciones IES', 'medio'))
    else:
        warnings.append('Sin minuta: complete los datos y las obligaciones manualmente. La consulta por número de proceso aún no está integrada.')
    if not obligations:
        warnings.append('No se extrajeron obligaciones IES. Agréguelas antes de generar el informe.')
    evidence = []
    for index, (name, data) in enumerate(expand_inputs(uploads), 1):
        digest = hashlib.sha256(data).hexdigest()
        try:
            _, pages = pdf_text(data)
            evidence.append(Evidence('E' + str(index), name, digest, pages))
        except Exception as error:
            evidence.append(Evidence('E' + str(index), name, digest, [], 'No legible: ' + str(error)))
            warnings.append(name + ': no se pudo extraer texto; requiere revisión manual.')
    if not evidence:
        raise ValueError('Cargue al menos una evidencia PDF.')
    return Report(process_number, fields, obligations, evidence, warnings)
