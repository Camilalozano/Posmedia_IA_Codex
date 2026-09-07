import io
import unittest
import zipfile
from lxml import etree as ET
from src.config import MASTER
from src.models import Field, Evidence, Report
from src.generation.word_report import build_docx, W


class WordTests(unittest.TestCase):
    def test_values_evidence_and_no_example_residue(self):
        original = MASTER.read_bytes()
        report = Report('PROC-TEST', {'numero_contrato_convenio': Field('CONV-TEST')},
                        [Field('1. Reportar avances ficticios.')],
                        [Evidence('E1', 'soporte.pdf', 'hash')],
                        activities={0: 'Se elaboró el informe de prueba.'}, links={0: ['E1']})
        data = build_docx(report)
        with zipfile.ZipFile(io.BytesIO(data)) as result, zipfile.ZipFile(MASTER) as source:
            self.assertIsNone(result.testzip())
            for name in source.namelist():
                if name != 'word/document.xml':
                    self.assertEqual(source.read(name), result.read(name))
            root = ET.fromstring(result.read('word/document.xml'))
            text = ''.join(root.itertext())
            self.assertIn('CONV-TEST', text)
            self.assertIn('Se elaboró el informe de prueba.', text)
            self.assertIn('E1 · soporte.pdf', text)
            self.assertNotIn('SICORE', text)
            self.assertNotIn('Automatizable', text)
            rows = root.findall('.//' + W + 'tbl')[1].findall(W + 'tr')
            self.assertEqual(len(rows), 2)
        self.assertEqual(original, MASTER.read_bytes())

    def test_requires_obligations(self):
        with self.assertRaises(ValueError):
            build_docx(Report('P', {}, [], []))
