import unittest
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.integrations.secop_documents import SecopDocuments
from tests.test_secop_lookup import csv_fixture, example

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_upload_review_generate_and_invalidate(self):
        data = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        self.assertFalse(app.exception)
        app.text_input[0].set_value('PROCESO-PRUEBA')
        app.file_uploader(key='minuta').set_value(('minuta.pdf', data, 'application/pdf'))
        app.file_uploader(key='evidencias').set_value([('evidencia.pdf', data, 'application/pdf')])
        next(x for x in app.button if x.label == 'Preparar borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.multiselect), 2)
        app.multiselect[0].set_value(['E1']).run()
        next(x for x in app.button if x.label == 'Generar informe Word').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('download_button')), 2)
        app.text_area[0].set_value('CONVENIO-CORREGIDO').run()
        self.assertEqual(len(app.get('download_button')), 0)
        app.text_input[0].set_value('OTRO-PROCESO').run()
        self.assertEqual(len(app.multiselect), 0)

    def test_lookup_prefills_report_and_base_change_invalidates_it(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        app.text_input[0].set_value('Atenea 582 2025')
        app.file_uploader(key='secop_base').set_value(('base.csv', csv_fixture([example()]), 'text/csv'))
        app.button(key='consultar_secop').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('ATENEA-582-2025' in item.value for item in app.success))
        data = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        app.file_uploader(key='evidencias').set_value([('evidencia.pdf', data, 'application/pdf')])
        next(x for x in app.button if x.label == 'Preparar borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_area[0].value, 'ATENEA-582-2025')
        app.file_uploader(key='secop_base').clear().run()
        self.assertEqual(len(app.text_area), 0)
        self.assertEqual(len(app.success), 0)

    def test_generate_word_without_evidence(self):
        data = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        app.text_input[0].set_value('PROCESO-PRUEBA')
        app.file_uploader(key='minuta').set_value(('minuta.pdf', data, 'application/pdf'))
        next(x for x in app.button if x.label == 'Preparar borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.multiselect), 0)
        self.assertTrue(any('No se cargaron evidencias' in item.value for item in app.warning))
        next(x for x in app.button if x.label == 'Generar informe Word').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('download_button')), 2)

    def test_sicore_and_social_security_are_added_to_evidence_inventory(self):
        data = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        app.text_input[0].set_value('PROCESO-PRUEBA')
        app.file_uploader(key='minuta').set_value(('minuta.pdf', data, 'application/pdf'))
        app.file_uploader(key='informe_sicore').set_value(('sicore.pdf', data, 'application/pdf'))
        app.file_uploader(key='planilla_seguridad_social').set_value(
            ('planilla.pdf', data + b'\n', 'application/pdf')
        )
        next(x for x in app.button if x.label == 'Preparar borrador').click().run()
        self.assertFalse(app.exception)
        names = [e.name for e in app.session_state['report'].evidence]
        self.assertIn('Informe SICORE · sicore.pdf', names)
        self.assertIn('Planilla Seguridad Social · planilla.pdf', names)

    def test_connection_error_tells_admin_to_replace_par(self):
        with patch.dict('os.environ', {}, clear=False):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20)
            app.secrets['ORACLE_PAR_URL'] = 'https://objectstorage.us-ashburn-1.oraclecloud.com/p/expired/file.csv'
            app.run()
            app.text_input[0].set_value('ATENEA-582-2025')
            with patch('src.integrations.secop_ui.lookup_oracle', side_effect=RuntimeError(
                    'No fue posible conectar con la base de Oracle. Revisa e ingresa un nuevo PAR en la configuración Secrets de Streamlit, con el nombre ORACLE_PAR_URL, y vuelve a intentar.')):
                app.button(key='consultar_secop').click().run()
            self.assertTrue(any('nuevo PAR' in item.value and 'ORACLE_PAR_URL' in item.value for item in app.error))

    def test_lookup_exposes_process_link_and_two_pdfs(self):
        minute_pdf = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        documents = SecopDocuments(
            minute_name='ATENEA-582-2025 EAN.pdf', minute_pdf=minute_pdf,
            process_name='Proceso_SECOP_ATENEA-IA-JE-003-2025.pdf',
            process_pdf=b'%PDF-process', process_reference='ATENEA-IA-JE-003-2025',
            archive_name='Documentos_SECOP_ATENEA-582-2025.zip', archive_bytes=b'PK-archive',
            archive_count=1, archive_inventory=[{
                'nombre_archivo': 'ATENEA-582-2025 EAN.pdf', 'extension': 'pdf',
                'tamano_bytes': len(minute_pdf), 'fecha_carga': '2025-12-23', 'estado': 'Descargado',
            }],
        )
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        app.text_input[0].set_value('Atenea 582 2025')
        app.file_uploader(key='secop_base').set_value(
            ('base.csv', csv_fixture([example(with_documents=True)]), 'text/csv')
        )
        with patch('src.integrations.secop_ui.cached_secop_documents', return_value=documents):
            app.button(key='consultar_secop').click().run()
        self.assertFalse(app.exception)
        labels = [button.label for button in app.get('download_button')]
        self.assertIn('Descargar minuta oficial (PDF)', labels)
        self.assertIn('Descargar ficha del proceso SECOP (PDF)', labels)
        self.assertIn('Descargar todos los documentos SECOP (ZIP)', labels)
        self.assertTrue(any('ATENEA-IA-JE-003-2025' in item.value for item in app.caption))
        self.assertTrue(any('Se extrajeron 2 obligaciones' in item.value for item in app.caption))

    def test_downloaded_minute_populates_review_and_obligations(self):
        minute_pdf = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        documents = SecopDocuments(
            minute_name='Minuta_ATENEA-999-2026.pdf', minute_pdf=minute_pdf,
            process_name='Proceso_SECOP_PRUEBA.pdf', process_pdf=b'%PDF-process',
            process_reference='PROCESO-PRUEBA', archive_name='Documentos_SECOP_PRUEBA.zip',
            archive_bytes=b'PK-archive', archive_count=2,
        )
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        app.text_input[0].set_value('Atenea 999 2026')
        app.file_uploader(key='secop_base').set_value(
            ('base.csv', csv_fixture([example('ATENEA-999-2026', with_documents=True)]), 'text/csv')
        )
        with patch('src.integrations.secop_ui.cached_secop_documents', return_value=documents):
            app.button(key='consultar_secop').click().run()
        self.assertTrue(any('Se usará automáticamente la minuta' in item.value for item in app.caption))
        next(x for x in app.button if x.label == 'Preparar borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_area[0].value, 'ATENEA-999-2026')
        obligations = next(area for area in app.text_area if area.label.startswith('Obligaciones'))
        self.assertIn('1. Reportar avances de formacion del periodo.', obligations.value)
        self.assertIn('2. Entregar un informe con sus evidencias.', obligations.value)
        archive = app.session_state['report'].contract_source['secop_documents_archive']
        self.assertEqual(archive['name'], 'Documentos_SECOP_PRUEBA.zip')
        self.assertEqual(archive['downloaded_documents'], 2)
