"""Combina la consulta contractual, la minuta y las evidencias del periodo."""
import hashlib
from src.models import Field, Evidence, Report
from src.extraction.pdf_reader import pdf_text
from src.extraction.contract_fields import extract_contract
from src.extraction.obligations import extract_obligations
from src.processing.batch import expand_inputs
from src.integrations.secop_lookup import normalize_reference
from src.config import NOT_FOUND


def extract_minute(name, data):
    """Extrae campos y obligaciones de una minuta, conservando su procedencia."""
    text, pages = pdf_text(data)
    fields = extract_contract(pages)
    for value in fields.values():
        if value.source.startswith('Página'):
            value.source = name + ' · ' + value.source
    obligations = []
    for item in extract_obligations(text, pages):
        body = item['obligaciones_especificas']
        location = f"página {item['pagina']}" if item.get('pagina') else 'sección compromisos específicos de la IES'
        obligations.append(Field(
            str(item['numero_obligacion']) + '. ' + body,
            name + ' · ' + location,
            'alto' if item.get('pagina') else 'medio',
        ))
    return fields, obligations


def prepare_report(process_number, contract, uploads, lookup=None, secop_documents=None):
    process_number = process_number.strip()
    if not process_number:
        raise ValueError('Indique el número de proceso.')
    fields = extract_contract([])
    obligations, warnings = [], []
    if contract:
        name, data = contract
        fields, obligations = extract_minute(name, data)
    else:
        warnings.append('Sin minuta: complete las obligaciones manualmente. Los campos contractuales pueden provenir de la base consultada.')
    if lookup:
        if normalize_reference(process_number) != normalize_reference(lookup.reference):
            raise ValueError('La consulta pertenece a otro proceso. Consulte de nuevo.')
        extracted = fields['numero_contrato_convenio'].value
        if contract and extracted != NOT_FOUND and normalize_reference(extracted) != normalize_reference(lookup.reference):
            raise ValueError('El número contractual extraído de la minuta difiere del contrato consultado. Revise la minuta antes de continuar.')
        if contract and extracted == NOT_FOUND:
            warnings.append('No se pudo comprobar el número de la minuta. Verifique que sus obligaciones correspondan al contrato consultado.')
        for key, value in lookup.fields.items():
            previous = fields.get(key)
            if value.value == NOT_FOUND:
                continue
            was_extracted = previous and ' · Página ' in previous.source
            if was_extracted and previous.value != NOT_FOUND and previous.value != value.value:
                warnings.append(f'{key.replace("_", " ")}: la base y la extracción de la minuta difieren. Se usó la base consultada; revise el dato.')
            fields[key] = value
        warnings.extend(lookup.warnings)
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
        warnings.append('No se cargaron evidencias. El informe indicará "Sin evidencia asociada" en las obligaciones.')
    report = Report(process_number, fields, obligations, evidence, warnings)
    if contract:
        report.contract_source['minute'] = {
            'name': contract[0],
            'sha256': hashlib.sha256(contract[1]).hexdigest(),
            'origin': 'SECOP automático o carga manual, según la selección mostrada en la interfaz',
        }
    archive_bytes = getattr(secop_documents, 'archive_bytes', b'') if secop_documents else b''
    if archive_bytes:
        report.contract_source['secop_documents_archive'] = {
            'name': getattr(secop_documents, 'archive_name', ''),
            'sha256': hashlib.sha256(archive_bytes).hexdigest(),
            'downloaded_documents': getattr(secop_documents, 'archive_count', 0),
            'purpose': 'Insumo conservado para etapas posteriores de explotación documental',
        }
    if lookup:
        report.contract_source.update({
            'source': lookup.source, 'sha256': lookup.sha256,
            'row': lookup.row_number, 'reference': lookup.reference,
            'raw_advance': lookup.raw_advance, 'advance_scale': 'valor original; sin transformación',
        })
    return report
