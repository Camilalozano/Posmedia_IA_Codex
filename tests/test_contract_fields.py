import unittest
from src.extraction.contract_fields import extract_contract
from src.config import NOT_FOUND, NO_CHANGES


class ContractTests(unittest.TestCase):
    def test_extract_number_and_source(self):
        fields = extract_contract(['Convenio No. ATENEA-999-2026\nObjeto: Desarrollar actividades de formación para estudiantes ficticios PLAZO doce meses'])
        self.assertEqual(fields['numero_contrato_convenio'].value, 'ATENEA-999-2026')
        self.assertIn('Página 1', fields['numero_contrato_convenio'].source)

    def test_missing_does_not_assert_no_modifications(self):
        fields = extract_contract([])
        self.assertEqual(fields['nombre_supervisor'].value, NOT_FOUND)
        self.assertEqual(fields['modificaciones'].value, NO_CHANGES)
