import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_upload_review_generate_and_invalidate(self):
        data = (ROOT / 'tests/fixtures/minuta_ejemplo.pdf').read_bytes()
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        self.assertFalse(app.exception)
        app.text_input[0].set_value('PROCESO-PRUEBA')
        app.file_uploader[0].set_value(('minuta.pdf', data, 'application/pdf'))
        app.file_uploader[1].set_value([('evidencia.pdf', data, 'application/pdf')])
        app.button[0].click().run()
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
