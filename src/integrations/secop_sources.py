"""Selección de soporte con obligaciones y lectura acotada de PDF dentro de ZIP."""
import hashlib
import io
import re
import zipfile
from src.config import NOT_FOUND
from src.extraction.pdf_reader import pdf_text
from src.extraction.obligations import extract_obligations, normalize_for_search
from src.extraction.contract_fields import extract_contract
from .secop_lookup import normalize_reference


def ranked_sources(rows, reference, provider_name):
    from .secop_documents import select_minute
    remaining = []
    for row in rows:
        name = normalize_for_search(str(row.get('nombre_archivo', '')))
        if any(word in name for word in ('INFORME', 'CUENTA', 'POLIZA', 'MODIFICACION', 'OTROSI', 'CESION', 'ADICION', 'ANTECEDENTE', 'EXPERIENCIA')):
            continue
        ext = str(row.get('extensi_n', '')).lower().lstrip('.')
        if ext == 'zip' or (ext == 'pdf' and (
            select_minute([row], reference, provider_name) is not None or
            any(word in name for word in ('CLAUSULADO', 'CONVENIO', 'ESTUDIO', 'PREVIO')))):
            remaining.append(row)
    def score(row):
        name = normalize_for_search(str(row.get('nombre_archivo', '')))
        return (100 * bool(normalize_reference(reference) and normalize_reference(reference) in normalize_reference(name))
                + 80 * any(w in name for w in ('MINUTA', 'CLAUSULADO', 'CONVENIO'))
                + 20 * ('PREVIO' in name))
    return sorted(remaining, key=score, reverse=True)


def select_source(rows, reference, provider_name, opener):
    from .secop_documents import SecopDocumentError, download_document, document_url, MAX_PDF_BYTES
    reused, failures, fallback = {}, [], None
    for row in ranked_sources(rows, reference, provider_name):
        url = document_url(row)
        try:
            data = download_document(url, opener=opener)
            # Reutilización limitada; los demás archivos se descargan al crear el ZIP.
            if sum(map(len, reused.values())) + len(data) <= 60 * 1024 * 1024:
                reused[url] = data
            candidates = []
            if str(row.get('extensi_n', '')).lower().lstrip('.') == 'zip':
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    members = archive.infolist()
                    if len(members) > 500 or sum(m.file_size for m in members) > 100 * 1024 * 1024:
                        raise SecopDocumentError('ZIP con más de 500 archivos o 100 MB descomprimidos.')
                    for member in members:
                        if member.is_dir() or not member.filename.lower().endswith('.pdf'):
                            continue
                        inner = {**row, 'nombre_archivo': member.filename.rsplit('/', 1)[-1].rsplit('\\', 1)[-1], 'extensi_n': 'pdf'}
                        if not ranked_sources([inner], reference, provider_name):
                            continue
                        if member.flag_bits & 1 or member.file_size > MAX_PDF_BYTES:
                            failures.append(member.filename + ': PDF cifrado o mayor de 20 MB.')
                            continue
                        with archive.open(member) as handle:
                            pdf = handle.read(MAX_PDF_BYTES + 1)
                        candidates.append((pdf, {**row, 'nombre_archivo': member.filename,
                                                '_archivo_zip': row.get('nombre_archivo'),
                                                '_zip_sha256': hashlib.sha256(data).hexdigest()}))
            else:
                candidates.append((data, row))
            for pdf, source in candidates:
                try:
                    if len(pdf) > MAX_PDF_BYTES or not pdf.lstrip().startswith(b'%PDF'):
                        raise ValueError('No es un PDF válido de hasta 20 MB.')
                    text, pages = pdf_text(pdf)
                    fields = extract_contract(pages)
                    number = fields['numero_contrato_convenio'].value
                    if number != NOT_FOUND and normalize_reference(number) != normalize_reference(reference):
                        failures.append(str(source['nombre_archivo']) + ': pertenece a otra referencia contractual.')
                        continue
                    if source.get('_asociacion') == 'proceso' and number == NOT_FOUND:
                        failures.append(str(source['nombre_archivo']) + ': no permite comprobar el contrato dentro de un proceso compartido.')
                        continue
                    item = (source['nombre_archivo'], pdf, source)
                    if extract_obligations(text, pages):
                        return item, reused, failures
                    if fallback is None:
                        fallback = item
                except ValueError as error:
                    failures.append(str(source.get('nombre_archivo', 'PDF')) + ': ' + str(error))
        except (SecopDocumentError, zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as error:
            failures.append(str(row.get('nombre_archivo', 'Documento')) + ': ' + str(error))
    return fallback, reused, failures
