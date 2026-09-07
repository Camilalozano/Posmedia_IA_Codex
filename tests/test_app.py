import unittest
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest
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
