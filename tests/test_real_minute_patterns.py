import unittest

from src.extraction.contract_fields import extract_contract
from src.extraction.obligations import extract_obligations


class RealMinutePatternTests(unittest.TestCase):
    def test_extracts_additional_contract_fields(self):
        pages = ['''
        CONVENIO POR RÉGIMEN PRIVADO No. ATENEA-582-2025
        por la otra, la UNIVERSIDAD EAN (asociada), identificada con NIT 860.026.058-1,
        representada legalmente por PERSONA DE PRUEBA, identificada con cédula de ciudadanía
        número 79.157.459. CUARTA. LUGAR DE EJECUCIÓN: Bogotá D.C. QUINTA. PLAZO DE
        EJECUCIÓN: El plazo de ejecución del convenio será hasta el 30 DE JUNIO DE 2031 SEXTA.
        La supervisión será ejercida por el Gerente de Educación Posmedia.
        VALOR ESTIMADO: el valor es $12.871.292.431. aporte de ATENEA $9.009.904.702.
        aporte de la IES $3.861.387.729.
        PRIMERA. OBJETO: Aunar esfuerzos técnicos, administrativos y financieros. SEGUNDA.
        ''']
        fields = extract_contract(pages)
        self.assertEqual(fields['numero_contrato_convenio'].value, 'ATENEA-582-2025')
        self.assertEqual(fields['nit_contratista'].value, '860.026.058-1')
        self.assertEqual(fields['cargo_supervisor'].value, 'Gerente de Educación Posmedia')
        self.assertEqual(fields['plazo'].value, 'hasta el 30 DE JUNIO DE 2031')
        self.assertEqual(fields['aporte_atenea'].value, '$9.009.904.702')

    def test_new_ies_heading_keeps_page_provenance(self):
        pages = [
            'Texto inicial',
            'C. COMPROMISOS ESPECÍFICOS DE LAS IES: 1. PRIMER COMPROMISO. 2. SEGUNDO',
            'COMPROMISO. 3. TERCER COMPROMISO. D. COMPROMISOS DE LA AGENCIA ATENEA',
        ]
        result = extract_obligations('\n'.join(pages), pages)
        self.assertEqual([item['numero_obligacion'] for item in result], [1, 2, 3])
        self.assertEqual([item['pagina'] for item in result], [2, 2, 3])


