import io
import unittest
import zipfile
from unittest.mock import patch
from src.config import NOT_FOUND
from src.models import Field
from src.extraction.obligations import extract_obligations
from src.integrations.secop_catalog import lookup_documents, DOCUMENT_DATASETS
from src.integrations.secop_sources import select_source
from src.integrations.secop_documents import SecopDocumentError


class CatalogTests(unittest.TestCase):
    def test_history_pagination_and_other_contract_exclusion(self):
        calls = []
        def query(endpoint, params, opener):
            calls.append((endpoint, params))
            if 'h4m3-b4e2' not in endpoint:
                return []
            if 'proceso' in params:
                return [{'id_documento': 'shared', 'proceso': 'CO1.BDOS.42'},
                        {'id_documento': 'other', 'proceso': 'CO1.BDOS.42', 'n_mero_de_contrato': 'CO1.PCCNTR.999'}]
            return [{'id_documento': str(params['$offset'] + i), 'proceso': 'CO1.BDOS.42',
                     'n_mero_de_contrato': 'CO1.PCCNTR.100'} for i in range(500 if params['$offset'] == 0 else 1)]
        rows, warnings = lookup_documents('CO1.PCCNTR.100', query, None)
        self.assertEqual(len(rows), 502)
        self.assertFalse(warnings)
        self.assertNotIn('other', [r['id_documento'] for r in rows])
        self.assertTrue(any(p.get('$offset') == 500 for _, p in calls))
        self.assertEqual(DOCUMENT_DATASETS['h4m3-b4e2'], 'Histórico 2025')

    def test_process_lookup_without_direct_documents(self):
        def query(endpoint, params, opener):
            if 'jbjy-vk9h' in endpoint:
                return [{'id_contrato': 'CO1.PCCNTR.100', 'proceso_de_compra': 'CO1.BDOS.42'}]
            if params.get('proceso') and 'dmgg-8hin' in endpoint:
                return [{'id_documento': 'ep', 'proceso': 'CO1.BDOS.42'}]
            return []
        rows, warnings = lookup_documents('CO1.PCCNTR.100', query, None)
        self.assertEqual(rows[0]['_asociacion'], 'proceso')
        self.assertFalse(warnings)

    def test_unavailable_sources_are_explicit(self):
        def query(*args):
            raise SecopDocumentError('HTTP 503')
        rows, warnings = lookup_documents('CO1.PCCNTR.100', query, None)
        self.assertEqual(rows, [])
        self.assertTrue(any('incompleta' in w for w in warnings))


class ExtractionTests(unittest.TestCase):
    def test_generic_specific_section_intro_does_not_close_section(self):
        pages = ['OBLIGACIONES ESPECÍFICAS DEL CONTRATISTA\nAdemás de las obligaciones generales:\n'
                 '2.1 apoyar la gestión.\n2.2 entregar informes.\n3. MODALIDAD DE SELECCIÓN\nTexto ajeno.']
        rows = extract_obligations('', pages)
        self.assertEqual([r['obligaciones_especificas'] for r in rows], ['apoyar la gestión.', 'entregar informes.'])

    def test_agency_specific_section_is_excluded(self):
        self.assertEqual(extract_obligations('OBLIGACIONES ESPECÍFICAS DE LA AGENCIA: 1. Pagar.'), [])

    def test_page_provenance_with_preface_before_first_number(self):
        pages = ['COMPROMISOS ESPECÍFICOS DE LAS IES:\nTexto introductorio largo.\n1. Reportar.',
                 '2. Entregar. D. COMPROMISOS DE LA AGENCIA: Pagar.']
        rows = extract_obligations('', pages)
        self.assertEqual([r['pagina'] for r in rows], [1, 2])

    def test_numbering_gap_is_preserved_and_flagged(self):
        rows = extract_obligations('OBLIGACIONES DE LA IES: 1. Reportar. 3. Entregar. D. OBLIGACIONES DE LA AGENCIA: Pagar.')
        self.assertEqual([r['numero_obligacion'] for r in rows], [1, 3])
        self.assertTrue(rows[0]['advertencias'])


class SourceTests(unittest.TestCase):
    @patch('src.integrations.secop_documents.download_document')
    def test_corrupt_pdf_does_not_prevent_next_candidate(self, download):
        from tests.test_secop_documents import simple_pdf
        valid = simple_pdf('OBLIGACIONES DE LA IES: 1. Reportar. D. OBLIGACIONES DE LA AGENCIA: Pagar.')
        download.side_effect = [b'%PDF-corrupt', valid]
        rows = [{'nombre_archivo': name, 'extensi_n': 'pdf', 'url_descarga_documento': str(i)}
                for i, name in enumerate(['MINUTA ATENEA-582-2025.pdf', 'CONVENIO ATENEA-582-2025.pdf'])]
        selected, _, failures = select_source(rows, 'ATENEA-582-2025', '', None)
        self.assertEqual(selected[1], valid)
        self.assertTrue(failures)

    @patch('src.integrations.secop_sources.extract_contract')
    @patch('src.integrations.secop_sources.pdf_text')
    @patch('src.integrations.secop_documents.download_document')
    def test_tries_next_pdf_when_first_has_no_specific_obligations(self, download, text, fields):
        download.side_effect = [b'%PDF-first', b'%PDF-second']
        text.side_effect = [('Texto general', ['Texto general']),
                            ('', ['OBLIGACIONES DE LA IES: 1. Reportar. D. OBLIGACIONES DE LA AGENCIA: Pagar.'])]
        fields.return_value = {'numero_contrato_convenio': Field('ATENEA-582-2025')}
        rows = [{'nombre_archivo': n, 'extensi_n': 'pdf', 'url_descarga_documento': str(i)}
                for i, n in enumerate(['MINUTA ATENEA-582-2025.pdf', 'CONVENIO ATENEA-582-2025.pdf'])]
        selected, reused, failures = select_source(rows, 'ATENEA-582-2025', '', None)
        self.assertEqual(selected[1], b'%PDF-second')

    @patch('src.integrations.secop_sources.extract_contract')
    @patch('src.integrations.secop_sources.pdf_text')
    @patch('src.integrations.secop_documents.download_document')
    def test_zip_source_and_shared_process_identity(self, download, text, fields):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('CARPETA/ESTUDIOS PREVIOS.pdf', b'%PDF-ep')
        download.return_value = buffer.getvalue()
        text.return_value = ('', ['OBLIGACIONES DE LA IES: 1. Reportar.'])
        fields.return_value = {'numero_contrato_convenio': Field('ATENEA-582-2025')}
        rows = [{'nombre_archivo': 'CARPETA.zip', 'extensi_n': 'zip', '_asociacion': 'proceso'}]
        selected, _, _ = select_source(rows, 'ATENEA-582-2025', '', None)
        self.assertEqual(selected[2]['_archivo_zip'], 'CARPETA.zip')
        fields.return_value = {'numero_contrato_convenio': Field(NOT_FOUND)}
        selected, _, failures = select_source(rows, 'ATENEA-582-2025', '', None)
        self.assertIsNone(selected)
        self.assertTrue(any('comprobar el contrato' in f for f in failures))
