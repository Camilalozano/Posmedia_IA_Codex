import io
import unittest
import zipfile
from pathlib import Path
from src.processing.pipeline import prepare_report
from src.processing.batch import expand_inputs
from src.config import NOT_FOUND

FIXTURE = Path(__file__).parent / 'fixtures' / 'minuta_ejemplo.pdf'


class PipelineTests(unittest.TestCase):
    def test_end_to_end_extraction(self):
        data = FIXTURE.read_bytes()
        report = prepare_report('PROC-123', ('minuta.pdf', data), [('evidencia.pdf', data)])
        self.assertEqual(report.process_number, 'PROC-123')
        self.assertEqual(report.fields['numero_contrato_convenio'].value, 'ATENEA-999-2026')
        self.assertEqual(len(report.obligations), 2)
        self.assertEqual(len(report.evidence), 1)

    def test_process_is_not_contract_and_bad_evidence_is_visible(self):
        report = prepare_report('PROC-123', None, [('ilegible.pdf', b'not a PDF')])
        self.assertEqual(report.fields['numero_contrato_convenio'].value, NOT_FOUND)
        self.assertTrue(report.evidence[0].status.startswith('No legible'))
        self.assertTrue(report.warnings)

    def test_dedup_and_reject_other_formats(self):
        self.assertEqual(len(expand_inputs([('a.pdf', b'a'), ('b.pdf', b'a')])), 1)
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as z:
            z.writestr('evidencia.exe', b'a')
        with self.assertRaises(ValueError):
            expand_inputs([('evidencias.zip', out.getvalue())])
