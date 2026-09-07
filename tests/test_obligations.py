import unittest
from src.extraction.obligations import extract_obligations


class ObligationTests(unittest.TestCase):
    def test_ies_section_stops_before_agency(self):
        text = ('OBLIGACIONES DE LA INSTITUCIÓN DE EDUCACIÓN SUPERIOR – IES: '
                '1. Reportar matrícula. 2. Entregar informe. '
                'D. OBLIGACIONES DE LA AGENCIA: 1. Transferir recursos.')
        rows = extract_obligations(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['obligaciones_especificas'], 'Entregar informe.')

    def test_other_party_is_not_ies(self):
        self.assertEqual(extract_obligations('OBLIGACIONES DE ATENEA: 1. Transferir recursos.'), [])

    def test_unicode_prefix_keeps_offsets(self):
        rows = extract_obligations('ß Información. OBLIGACIONES DE LA IES: 1. Reportar avances.')
        self.assertEqual(rows[0]['obligaciones_especificas'], 'Reportar avances.')
