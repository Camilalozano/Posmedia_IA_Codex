import io
import json
import unittest
import zipfile
from email.message import Message
from urllib.error import HTTPError
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pymupdf

from src.integrations.secop_documents import (
    SecopDocumentError, build_documents_archive, build_process_pdf, extract_process_reference,
    notice_uid, prepare_secop_documents, select_minute,
)


PROCESS_URL = ('https://community.secop.gov.co/Public/Tendering/OpportunityDetail/'
               'Index?noticeUID=CO1.NTC.8836482&isFromPublicArea=True')


def simple_pdf(text):
    document = pymupdf.open()
    page = document.new_page()
    suffix = ' Documento contractual de prueba con texto suficiente para validar la extracción automática.'
    page.insert_textbox((72, 72, 520, 300), text + suffix * 3)
    data = document.tobytes()
    document.close()
    return data


class Response:
    def __init__(self, data):
        self.data = data
        self.headers = {'Content-Length': str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size):
        return self.data[:size]


class SecopDocumentTests(unittest.TestCase):
    def test_notice_uid_only_accepts_expected_secop_url(self):
        self.assertEqual(notice_uid(PROCESS_URL), 'CO1.NTC.8836482')
        with self.assertRaises(SecopDocumentError):
            notice_uid('https://example.com/?noticeUID=CO1.NTC.8836482')

    def test_select_minute_prefers_contract_pdf(self):
        rows = [
            {'nombre_archivo': 'Poliza ATENEA-582-2025.pdf', 'extensi_n': 'pdf'},
            {'nombre_archivo': 'ATENEA-582-2025 EAN.pdf', 'extensi_n': 'pdf'},
            {'nombre_archivo': 'Anexo.xlsx', 'extensi_n': 'xlsx'},
        ]
        selected = select_minute(rows, 'ATENEA-582-2025', 'UNIVERSIDAD EAN')
        self.assertEqual(selected['nombre_archivo'], 'ATENEA-582-2025 EAN.pdf')

    def test_reference_and_process_pdf(self):
        minute = simple_pdf('Convenio derivado del proceso ATENEA-IA-JE-003-2025')
        self.assertEqual(extract_process_reference(minute), 'ATENEA-IA-JE-003-2025')
        process = build_process_pdf({
            'entidad': 'AGENCIA ATENEA',
            'referencia_del_proceso': 'ATENEA-IA-JE-003-2025',
            'nombre_del_proveedor': 'UNIVERSIDAD EAN',
        }, PROCESS_URL)
        self.assertTrue(process.startswith(b'%PDF'))
        with pymupdf.open(stream=process, filetype='pdf') as document:
            text = ''.join(page.get_text() for page in document)
        self.assertIn('Ficha del proceso SECOP II', text)
        self.assertIn('Datos Abiertos de Colombia', text)

    def test_complete_retrieval_uses_official_rows_and_download_headers(self):
        minute_pdf = simple_pdf('Proceso ATENEA-IA-JE-003-2025')
        download_url = ('https://community.secop.gov.co/Public/Archive/RetrieveFile/Index?'
                        'DocumentId=724204637&InCommunity=False')
        document_rows = [{
            'nombre_archivo': 'ATENEA-582-2025 EAN.pdf',
            'extensi_n': 'pdf',
            'url_descarga_documento': {'url': download_url},
        }]
        process_rows = [
            {
                'referencia_del_proceso': 'ATENEA-IA-JE-003-2025',
                'nombre_del_proveedor': 'OTRO',
                'nit_del_proveedor_adjudicado': '999',
                'urlproceso': {'url': PROCESS_URL},
            },
            {
                'referencia_del_proceso': 'ATENEA-IA-JE-003-2025',
                'nombre_del_proveedor': 'UNIVERSIDAD EAN',
                'nit_del_proveedor_adjudicado': '860026058',
                'urlproceso': {'url': PROCESS_URL},
            },
        ]
        requests = []

        def opener(request, timeout):
            requests.append(request)
            parsed = urlparse(request.full_url)
            if parsed.netloc == 'www.datos.gov.co' and parsed.path.endswith('dmgg-8hin.json'):
                self.assertEqual(parse_qs(parsed.query)['n_mero_de_contrato'], ['CO1.PCCNTR.8724386'])
                return Response(json.dumps(document_rows).encode())
            if parsed.netloc == 'www.datos.gov.co' and parsed.path.endswith('p6dx-8zbt.json'):
                self.assertEqual(parse_qs(parsed.query)['referencia_del_proceso'], ['ATENEA-IA-JE-003-2025'])
                return Response(json.dumps(process_rows).encode())
            self.assertEqual(request.get_header('Referer'), 'https://community.secop.gov.co/')
            return Response(minute_pdf)

        result = prepare_secop_documents(
            PROCESS_URL, 'CO1.PCCNTR.8724386', 'ATENEA-582-2025',
            '860026058', 'UNIVERSIDAD EAN', opener=opener,
        )
        self.assertEqual(result.minute_pdf, minute_pdf)
        self.assertTrue(result.process_pdf.startswith(b'%PDF'))
        self.assertEqual(result.process_reference, 'ATENEA-IA-JE-003-2025')
        self.assertEqual(result.archive_count, 1)
        with zipfile.ZipFile(io.BytesIO(result.archive_bytes)) as archive:
            self.assertIn('ATENEA-582-2025 EAN.pdf', archive.namelist())
            self.assertIn('inventario_documentos_secop.csv', archive.namelist())
        self.assertEqual(len(requests), 3)

    def test_archive_includes_every_supported_file_without_expanding_nested_zip(self):
        base = 'https://community.secop.gov.co/Public/Archive/RetrieveFile/Index?DocumentId='
        rows = [
            {'id_documento': '1', 'nombre_archivo': 'contrato.pdf', 'extensi_n': 'pdf',
             'tamanno_archivo': '3', 'url_descarga_documento': {'url': base + '1'}},
            {'id_documento': '2', 'nombre_archivo': 'anexo.xlsx', 'extensi_n': 'xlsx',
             'tamanno_archivo': '4', 'url_descarga_documento': {'url': base + '2'}},
            {'id_documento': '3', 'nombre_archivo': 'soportes.zip', 'extensi_n': 'zip',
             'tamanno_archivo': '5', 'url_descarga_documento': {'url': base + '3'}},
        ]
        payloads = {base + '1': b'pdf', base + '2': b'xlsx', base + '3': b'zip00'}
        name, data, inventory, warnings = build_documents_archive(
            rows, 'ATENEA-582-2025', opener=lambda request, timeout: Response(payloads[request.full_url]),
        )
        self.assertEqual(name, 'Documentos_SECOP_ATENEA-582-2025.zip')
        self.assertFalse(warnings)
        self.assertEqual(len(inventory), 3)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {'contrato.pdf', 'anexo.xlsx', 'soportes.zip', 'inventario_documentos_secop.csv'},
            )
            self.assertEqual(archive.read('soportes.zip'), b'zip00')

    def test_transient_api_error_is_retried(self):
        calls = 0

        def opener(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise HTTPError(request.full_url, 503, 'Unavailable', Message(), None)
            return Response(b'[]')

        from src.integrations.secop_documents import _api_rows, DOCUMENTS_API
        with patch('src.integrations.secop_documents.time.sleep'):
            self.assertEqual(_api_rows(DOCUMENTS_API, {'$limit': 1}, opener), [])
        self.assertEqual(calls, 2)

    def test_minute_remains_available_when_process_api_fails(self):
        minute_pdf = simple_pdf('Proceso ATENEA-IA-JE-003-2025')
        download_url = ('https://community.secop.gov.co/Public/Archive/RetrieveFile/Index?'
                        'DocumentId=724204637')
        document_rows = [{
            'nombre_archivo': 'ATENEA-582-2025 EAN.pdf', 'extensi_n': 'pdf',
            'url_descarga_documento': {'url': download_url},
        }]

        def opener(request, timeout):
            if 'dmgg-8hin.json' in request.full_url:
                return Response(json.dumps(document_rows).encode())
            if request.full_url == download_url:
                return Response(minute_pdf)
            raise HTTPError(request.full_url, 503, 'Unavailable', Message(), None)

        with patch('src.integrations.secop_documents.time.sleep'):
            result = prepare_secop_documents(
                PROCESS_URL, 'CO1.PCCNTR.8724386', 'ATENEA-582-2025',
                '860026058', 'UNIVERSIDAD EAN', opener=opener,
            )
        self.assertEqual(result.minute_pdf, minute_pdf)
        self.assertEqual(result.process_pdf, b'')
        self.assertTrue(any('minuta sí quedó disponible' in warning for warning in result.warnings))
