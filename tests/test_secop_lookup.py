import csv
import io
import unittest
from email.message import Message
from urllib.error import HTTPError, URLError
from openpyxl import Workbook
from src.config import NOT_FOUND
from src.integrations.secop_lookup import (
    ADVANCE, FIELD_MAP, REFERENCE, OracleConnectionError, download_oracle_csv,
    lookup_file, lookup_oracle, normalize_reference,
)
from src.processing.pipeline import prepare_report


def csv_fixture(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(FIELD_MAP.values()) + [ADVANCE])
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8-sig')


def example(reference='ATENEA-582-2025'):
    return {
        REFERENCE: reference,
        FIELD_MAP['nombre_contratista_asociado']: 'INSTITUCIÓN FICTICIA',
        FIELD_MAP['nombre_supervisor']: 'SUPERVISOR FICTICIO',
        FIELD_MAP['fecha_terminacion']: '2032-12-31 00:00:00',
        FIELD_MAP['modificaciones']: 'Prórroga',
        FIELD_MAP['objeto']: 'Objeto ficticio; verificar la lectura íntegra, sin recortes.',
        ADVANCE: '1000',
    }


class LookupTests(unittest.TestCase):
    def test_oracle_download_and_lookup(self):
        data = csv_fixture([example()])
        class Response:
            headers = {'Content-Length': str(len(data))}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return data[:size]
        result = lookup_oracle(
            'https://objectstorage.us-ashburn-1.oraclecloud.com/p/secret/object.csv',
            'Atenea 582 2025', opener=lambda request, timeout: Response())
        self.assertEqual(result.reference, 'ATENEA-582-2025')
        self.assertNotIn('secret', result.source)

    def test_oracle_errors_request_new_par_without_leaking_url(self):
        url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/p/very-secret/object.csv'
        cases = [
            lambda request, timeout: (_ for _ in ()).throw(HTTPError(url, 404, 'Not found', Message(), None)),
            lambda request, timeout: (_ for _ in ()).throw(URLError('offline')),
        ]
        for opener in cases:
            with self.subTest(opener=opener), self.assertRaises(OracleConnectionError) as raised:
                download_oracle_csv(url, opener=opener)
            message = str(raised.exception)
            self.assertIn('nuevo PAR', message)
            self.assertIn('ORACLE_PAR_URL', message)
            self.assertNotIn('very-secret', message)

    def test_oracle_rejects_wrong_destination(self):
        with self.assertRaisesRegex(OracleConnectionError, 'PAR inválido'):
            download_oracle_csv('https://example.com/file.csv')

    def test_xlsx_reader_and_empty_other_sheet(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'tabla_maestra_completa'
        row = example()
        sheet.append(list(row))
        sheet.append(list(row.values()))
        workbook.create_sheet('Hoja1')
        buffer = io.BytesIO()
        workbook.save(buffer)
        workbook.close()
        result = lookup_file('base.xlsx', buffer.getvalue(), 'Atenea 582 2025')
        self.assertEqual(result.reference, 'ATENEA-582-2025')
        self.assertEqual(result.fields['fecha_terminacion'].value, '31/12/2032')
        self.assertIn('tabla_maestra_completa', result.source)

    def test_reference_variants_preserve_original(self):
        data = csv_fixture([example()])
        for query in ['ATENEA-582-2025', 'Atenea-582-2025', 'Atenea 582 2025',
                      'atenea5822025', ' ATENEA–582—2025 ', 'Atenea\t582\u00a02025']:
            with self.subTest(query=query):
                result = lookup_file('base.csv', data, query)
                self.assertEqual(result.reference, 'ATENEA-582-2025')
                self.assertEqual(result.fields['fecha_terminacion'].value, '31/12/2032')
                self.assertEqual(result.fields['objeto'].value, example()[FIELD_MAP['objeto']])

    def test_no_partial_or_zero_removal_or_blank_matches(self):
        data = csv_fixture([example('ATENEA-003-2025')])
        self.assertIsNone(lookup_file('base.csv', data, '003'))
        self.assertIsNone(lookup_file('base.csv', data, 'ATENEA-3-2025'))
        with self.assertRaises(ValueError):
            lookup_file('base.csv', data, ' - ')

    def test_collision_never_picks_first(self):
        with self.assertRaisesRegex(ValueError, 'varios registros'):
            lookup_file('base.csv', csv_fixture([example(), example('Atenea 582 2025')]), 'atenea5822025')

    def test_unknown_scale_and_missing_values_not_invented(self):
        row = example()
        row[FIELD_MAP['nombre_supervisor']] = ''
        row[FIELD_MAP['modificaciones']] = ''
        result = lookup_file('base.csv', csv_fixture([row]), 'ATENEA5822025')
        self.assertEqual(result.fields['porcentaje_avance'].value, NOT_FOUND)
        self.assertEqual(result.raw_advance, '1000')
        self.assertEqual(result.fields['modificaciones'].value, NOT_FOUND)
        self.assertNotIn('cargo_supervisor', result.fields)
        self.assertTrue(result.warnings)

    def test_report_uses_mapping_and_keeps_provenance(self):
        result = lookup_file('base.csv', csv_fixture([example()]), 'atenea5822025')
        report = prepare_report('Atenea 582 2025', None, [('soporte.pdf', b'bad pdf')], lookup=result)
        self.assertEqual(report.fields['numero_contrato_convenio'].value, 'ATENEA-582-2025')
        self.assertEqual(report.contract_source['sha256'], result.sha256)
        self.assertEqual(report.contract_source['row'], 2)
        self.assertIn('base.csv', report.fields['objeto'].source)
        with self.assertRaisesRegex(ValueError, 'otro proceso'):
            prepare_report('ATENEA-583-2025', None, [], lookup=result)

    def test_bad_schema(self):
        with self.assertRaisesRegex(ValueError, 'columna requerida'):
            lookup_file('base.csv', b'numero,valor\nATENEA-582-2025,1', 'atenea5822025')
