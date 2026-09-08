"""Recupera la minuta y construye una ficha PDF desde Datos Abiertos de SECOP II."""
import csv
import hashlib
import io
import json
import re
import textwrap
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

import pymupdf

from src.extraction.pdf_reader import pdf_text
from src.integrations.secop_lookup import normalize_reference

DOCUMENTS_API = 'https://www.datos.gov.co/resource/dmgg-8hin.json'
PROCESSES_API = 'https://www.datos.gov.co/resource/p6dx-8zbt.json'
MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_BYTES = 30 * 1024 * 1024
MAX_ARCHIVE_SOURCE_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_DOCUMENTS = 100
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Posmedia-IA-Codex/0.4'


class SecopDocumentError(RuntimeError):
    """Error de recuperación seguro para mostrar en la interfaz."""


@dataclass
class SecopDocuments:
    minute_name: str = ''
    minute_pdf: bytes = b''
    process_name: str = ''
    process_pdf: bytes = b''
    process_reference: str = ''
    archive_name: str = ''
    archive_bytes: bytes = b''
    archive_count: int = 0
    archive_inventory: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def notice_uid(process_url: str) -> str:
    parsed = urlparse(str(process_url).strip())
    if parsed.scheme != 'https' or parsed.hostname != 'community.secop.gov.co':
        raise SecopDocumentError('La base no contiene una URL válida del proceso SECOP II.')
    value = parse_qs(parsed.query).get('noticeUID', [''])[0]
    if not re.fullmatch(r'CO1\.NTC\.\d+', value, re.I):
        raise SecopDocumentError('La URL del proceso no contiene un identificador SECOP válido.')
    return value.upper()


def _read(request: Request, limit: int, opener=urlopen) -> bytes:
    data = b''
    for attempt in range(3):
        try:
            with opener(request, timeout=30) as response:
                declared = response.headers.get('Content-Length')
                if declared and int(declared) > limit:
                    raise SecopDocumentError('El archivo de SECOP supera el límite permitido.')
                data = response.read(limit + 1)
            break
        except SecopDocumentError:
            raise
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise SecopDocumentError(
                    'No fue posible recuperar los documentos públicos de SECOP. Intente nuevamente.'
                ) from None
        except (URLError, TimeoutError, OSError, ValueError):
            if attempt == 2:
                raise SecopDocumentError(
                    'No fue posible recuperar los documentos públicos de SECOP. Intente nuevamente.'
                ) from None
        time.sleep(0.5 * (attempt + 1))
    if not data or len(data) > limit:
        raise SecopDocumentError('La respuesta de SECOP está vacía o supera el límite permitido.')
    return data


def _api_rows(endpoint: str, params: dict, opener=urlopen) -> list[dict]:
    url = endpoint + '?' + urlencode(params)
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    data = _read(request, MAX_JSON_BYTES, opener)
    try:
        result = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SecopDocumentError('Datos Abiertos de SECOP devolvió una respuesta incompatible.') from None
    if not isinstance(result, list):
        raise SecopDocumentError('Datos Abiertos de SECOP devolvió una respuesta incompatible.')
    return result


def _digits(value: str) -> str:
    return re.sub(r'\D', '', str(value or ''))


def select_minute(rows: list[dict], reference: str, provider_name: str) -> dict | None:
    key = normalize_reference(reference)
    provider_tokens = [token for token in re.findall(r'[A-Z0-9]{3,}', provider_name.upper())
                       if token not in {'UNIVERSIDAD', 'FUNDACION', 'CORPORACION'}]
    ranked = []
    for row in rows:
        name = str(row.get('nombre_archivo', ''))
        if str(row.get('extensi_n', '')).lower() != 'pdf':
            continue
        upper = name.upper()
        score = 0
        if key and key in normalize_reference(name):
            score += 100
        if 'MINUTA' in upper:
            score += 50
        if any(token in upper for token in provider_tokens):
            score += 20
        if any(term in upper for term in ('PÓLIZA', 'POLIZA', 'RP ', 'FIRMADO', 'EN EJECUCIÓN', 'EN EJECUCION', 'ALCANCE')):
            score -= 100
        ranked.append((score, name, row))
    if not ranked:
        return None
    score, _, row = max(ranked, key=lambda item: (item[0], item[1]))
    return row if score > 0 else None


def download_document(url: str, limit=MAX_DOCUMENT_BYTES, opener=urlopen) -> bytes:
    parsed = urlparse(str(url).strip())
    if (parsed.scheme != 'https' or parsed.hostname != 'community.secop.gov.co'
            or parsed.path != '/Public/Archive/RetrieveFile/Index'):
        raise SecopDocumentError('SECOP entregó un enlace de documento no permitido.')
    request = Request(url, headers={
        'User-Agent': USER_AGENT,
        'Referer': 'https://community.secop.gov.co/',
        'Accept': '*/*',
    })
    return _read(request, limit, opener)


def download_pdf(url: str, opener=urlopen) -> bytes:
    data = download_document(url, MAX_PDF_BYTES, opener)
    if not data.startswith(b'%PDF'):
        raise SecopDocumentError('SECOP no devolvió la minuta en formato PDF.')
    return data


def document_url(row: dict) -> str:
    link = row.get('url_descarga_documento', {})
    return link.get('url', '') if isinstance(link, dict) else str(link)


def safe_archive_name(name: str, fallback: str) -> str:
    cleaned = str(name or '').replace('\\', '_').replace('/', '_')
    cleaned = re.sub(r'[\x00-\x1f<>:"|?*]', '_', cleaned).strip(' .')
    return (cleaned or fallback)[:180]


def build_documents_archive(rows: list[dict], reference: str, reused: dict[str, bytes] | None = None,
                            opener=urlopen) -> tuple[str, bytes, list[dict], list[str]]:
    """Descarga los archivos del contrato y los empaqueta sin expandir archivos internos."""
    if len(rows) > MAX_ARCHIVE_DOCUMENTS:
        raise SecopDocumentError(
            f'El contrato tiene más de {MAX_ARCHIVE_DOCUMENTS} documentos; no se generó el ZIP automático.'
        )
    declared_total = 0
    for row in rows:
        try:
            declared_total += int(float(str(row.get('tamanno_archivo', '') or 0).replace(',', '.')))
        except ValueError:
            pass
    if declared_total > MAX_ARCHIVE_SOURCE_BYTES:
        raise SecopDocumentError('Los documentos del contrato superan 100 MB; no se generó el ZIP automático.')

    reused = reused or {}
    inventory, warnings, used_names = [], [], set()
    total = 0
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for index, row in enumerate(rows, 1):
            original_name = str(row.get('nombre_archivo') or f'documento_{index}')
            name = safe_archive_name(original_name, f'documento_{index}')
            if name.casefold() in used_names:
                stem, dot, suffix = name.rpartition('.')
                name = f'{stem or name}_{row.get("id_documento", index)}{dot}{suffix}' if dot else f'{name}_{index}'
            used_names.add(name.casefold())
            url = document_url(row)
            status = 'Descargado'
            data = reused.get(url)
            try:
                if data is None:
                    data = download_document(url, opener=opener)
                total += len(data)
                if total > MAX_ARCHIVE_SOURCE_BYTES:
                    raise SecopDocumentError('Los documentos descargados superan 100 MB.')
                archive.writestr(name, data)
                digest = hashlib.sha256(data).hexdigest()
            except SecopDocumentError as error:
                data, digest, status = b'', '', 'No descargado: ' + str(error)
                warnings.append(original_name + ': no fue posible descargar este archivo.')
            inventory.append({
                'id_documento': str(row.get('id_documento', '')),
                'nombre_archivo': original_name,
                'archivo_en_zip': name if data else '',
                'extension': str(row.get('extensi_n', '')),
                'tamano_bytes': len(data),
                'fecha_carga': str(row.get('fecha_carga', '')),
                'descripcion': str(row.get('descripci_n', '')),
                'estado': status,
                'sha256': digest,
                'url_descarga': url,
            })
        manifest = io.StringIO(newline='')
        columns = list(inventory[0]) if inventory else ['estado']
        writer = csv.DictWriter(manifest, fieldnames=columns)
        writer.writeheader()
        writer.writerows(inventory)
        archive.writestr('inventario_documentos_secop.csv', '\ufeff' + manifest.getvalue())
    reference_name = safe_archive_name(reference, 'contrato')
    return f'Documentos_SECOP_{reference_name}.zip', output.getvalue(), inventory, warnings


def extract_process_reference(minute_pdf: bytes) -> str:
    text, _ = pdf_text(minute_pdf)
    patterns = [
        r'\bproceso\s+(ATENEA-[A-Z0-9]+(?:-[A-Z0-9]+)+-20\d{2})\b',
        r'\bconvocatoria\s+(ATENEA-[A-Z0-9]+(?:-[A-Z0-9]+)+-20\d{2})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).upper()
    return ''


def select_process(rows: list[dict], expected_notice: str, provider_document: str) -> dict | None:
    valid = []
    for row in rows:
        source = row.get('urlproceso', {})
        url = source.get('url', '') if isinstance(source, dict) else str(source)
        try:
            if notice_uid(url) == expected_notice:
                valid.append(row)
        except SecopDocumentError:
            continue
    if not valid:
        return None
    provider_key = _digits(provider_document)
    if provider_key:
        matching = [row for row in valid if _digits(row.get('nit_del_proveedor_adjudicado')) == provider_key]
        if matching:
            return matching[0]
    return valid[0]


PROCESS_FIELDS = [
    ('Entidad', 'entidad'),
    ('NIT de la entidad', 'nit_entidad'),
    ('Referencia del proceso', 'referencia_del_proceso'),
    ('ID del proceso', 'id_del_proceso'),
    ('ID del portafolio', 'id_del_portafolio'),
    ('Nombre del procedimiento', 'nombre_del_procedimiento'),
    ('Descripción', 'descripci_n_del_procedimiento'),
    ('Fase', 'fase'),
    ('Estado del procedimiento', 'estado_del_procedimiento'),
    ('Estado resumen', 'estado_resumen'),
    ('Fecha de publicación', 'fecha_de_publicacion_del'),
    ('Precio base', 'precio_base'),
    ('Modalidad de contratación', 'modalidad_de_contratacion'),
    ('Justificación de modalidad', 'justificaci_n_modalidad_de'),
    ('Tipo de contrato', 'tipo_de_contrato'),
    ('Proveedor adjudicado', 'nombre_del_proveedor'),
    ('NIT del proveedor', 'nit_del_proveedor_adjudicado'),
    ('Fecha de adjudicación', 'fecha_adjudicacion'),
    ('Valor adjudicado', 'valor_total_adjudicacion'),
    ('Código UNSPSC principal', 'codigo_principal_de_categoria'),
]


def build_process_pdf(row: dict, source_url: str) -> bytes:
    document = pymupdf.open()
    page = None
    y = 72

    def new_page():
        nonlocal page, y
        page = document.new_page(width=595, height=842)
        y = 72
        page.insert_text((54, 40), 'Ficha del proceso SECOP II', fontsize=16, fontname='hebo', color=(0.05, 0.25, 0.45))
        page.insert_text((54, 58), 'Generada desde Datos Abiertos de Colombia', fontsize=9, fontname='helv', color=(0.3, 0.3, 0.3))

    def add_field(label: str, value: str, break_long_words=False, uri=''):
        nonlocal y
        value = str(value or '').strip()
        if not value:
            return
        lines = textwrap.wrap(
            value, width=92, break_long_words=break_long_words,
            break_on_hyphens=break_long_words,
        ) or ['']
        needed = 18 + 13 * len(lines)
        if page is None or y + needed > 790:
            new_page()
        page.insert_text((54, y), label + ':', fontsize=9, fontname='hebo', color=(0.15, 0.15, 0.15))
        y += 13
        link_top = y - 10
        for line in lines:
            page.insert_text((66, y), line, fontsize=9, fontname='helv', color=(0, 0, 0))
            y += 12
        if uri:
            page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(62, link_top, 540, y), 'uri': uri})
        y += 6

    new_page()
    for label, key in PROCESS_FIELDS:
        value = row.get(key, '')
        if key in {'fecha_de_publicacion_del', 'fecha_adjudicacion'} and value:
            try:
                value = datetime.fromisoformat(str(value).replace('Z', '+00:00')).strftime('%d/%m/%Y')
            except ValueError:
                pass
        if key in {'precio_base', 'valor_total_adjudicacion'} and str(value).strip():
            try:
                value = '$' + f'{int(float(value)):,}'.replace(',', '.')
            except ValueError:
                pass
        add_field(label, value)
    add_field('Fuente', 'SECOP II - Procesos de Contratación, Datos Abiertos Colombia (p6dx-8zbt)')
    uid = notice_uid(source_url)
    add_field('Proceso en SECOP II', 'community.secop.gov.co · noticeUID=' + uid, uri=source_url)
    for number, output_page in enumerate(document, 1):
        output_page.insert_text((500, 820), f'Página {number}', fontsize=8, fontname='helv', color=(0.35, 0.35, 0.35))
    data = document.tobytes(garbage=4, deflate=True)
    document.close()
    return data


def prepare_secop_documents(process_url: str, contract_id: str, reference: str,
                            provider_document: str, provider_name: str,
                            opener=urlopen) -> SecopDocuments:
    uid = notice_uid(process_url)
    if not re.fullmatch(r'CO1\.PCCNTR\.\d+', str(contract_id), re.I):
        raise SecopDocumentError('La base no informa un identificador contractual válido para buscar la minuta.')
    rows = _api_rows(DOCUMENTS_API, {
        'n_mero_de_contrato': contract_id,
        '$limit': 500,
    }, opener)
    if not rows:
        raise SecopDocumentError('No se encontraron documentos públicos asociados al id_contrato consultado.')
    minute = select_minute(rows, reference, provider_name)
    if minute is None:
        result = SecopDocuments()
        try:
            archive_name, archive_bytes, inventory, archive_warnings = build_documents_archive(
                rows, reference, opener=opener,
            )
            result.archive_name = archive_name
            result.archive_bytes = archive_bytes
            result.archive_count = sum(item['estado'] == 'Descargado' for item in inventory)
            result.archive_inventory = inventory
            result.warnings.extend(archive_warnings)
        except SecopDocumentError as error:
            result.warnings.append(str(error))
        result.warnings.append('No se identificó una minuta PDF dentro de los documentos asociados al contrato.')
        return result
    minute_url = document_url(minute)
    minute_pdf = download_pdf(minute_url, opener)
    result = SecopDocuments(
        minute_name=str(minute.get('nombre_archivo') or f'Minuta_{reference}.pdf'),
        minute_pdf=minute_pdf,
    )
    try:
        archive_name, archive_bytes, inventory, archive_warnings = build_documents_archive(
            rows, reference, reused={minute_url: minute_pdf}, opener=opener,
        )
        result.archive_name = archive_name
        result.archive_bytes = archive_bytes
        result.archive_count = sum(item['estado'] == 'Descargado' for item in inventory)
        result.archive_inventory = inventory
        result.warnings.extend(archive_warnings)
    except SecopDocumentError as error:
        result.warnings.append(str(error))
    try:
        process_reference = extract_process_reference(minute_pdf)
    except ValueError:
        process_reference = ''
    if not process_reference:
        result.warnings.append('La minuta fue localizada, pero no permitió identificar la referencia del proceso SECOP.')
        return result
    result.process_reference = process_reference
    try:
        process_rows = _api_rows(PROCESSES_API, {
            'referencia_del_proceso': process_reference,
            '$limit': 200,
        }, opener)
    except SecopDocumentError as error:
        result.warnings.append(str(error) + ' La minuta sí quedó disponible; vuelva a consultar para generar la ficha.')
        return result
    process = select_process(process_rows, uid, provider_document)
    if process is None:
        result.warnings.append('No se encontró la ficha del proceso en Datos Abiertos de SECOP. La minuta sí quedó disponible.')
        return result
    result.process_name = f'Proceso_SECOP_{process_reference}.pdf'
    result.process_pdf = build_process_pdf(process, process_url)
    return result
