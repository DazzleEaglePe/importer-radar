"""Pruebas de parse_ficha.py con fichas INVENTADAS que copian la estructura real de la consulta RUC.

Las fichas reales (con datos de empresas y personas) viven solo en data/, fuera de git. Si esa carpeta existe en
tu equipo, al final se prueba además que todas las fichas reales se lean sin error.

Uso: python3 -I scripts/spike/test_parse_ficha.py
"""
import contextlib
import io
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import parse_ficha as pf  # noqa: E402
from test_lookup_fetch import mk  # noqa: E402


def item(label, value_html):
    return ('<div class="list-group-item"><div class="row"><div class="col-sm-5">'
            f'<h4 class="list-group-item-heading">{label}</h4></div><div class="col-sm-7">{value_html}</div></div></div>')


def p(v):
    return f'<p class="list-group-item-text">{v}</p>'


def table(rows):
    return '<table class="table tblResultado"><tbody>' + ''.join(f'<tr><td>{r}</td></tr>' for r in rows) + '</tbody></table>'


def ficha(ruc=None, **over):
    ruc = ruc or mk(1)
    parts = {
        'cabecera': f'<h4 class="list-group-item-heading">{ruc} - EMPRESA DE PRUEBA S.A.C.</h4>',
        'tipo': p('SOCIEDAD ANONIMA CERRADA'),
        'comercial': p('-'),
        'inscripcion': p('12/03/2015'),
        'inicio': p('12/03/2015'),
        'estado': p('ACTIVO'),
        'condicion': p('HABIDO'),
        'domicilio': p('AV. PRUEBA 123 LIMA - LIMA - LIMA'),
        'sist_emision': p('MANUAL/COMPUTARIZADO'),
        'comext': p('IMPORTADOR/EXPORTADOR'),
        'contab': p('COMPUTARIZADO'),
        'actividades': table(['Principal    - 4652 - VENTA AL POR MAYOR DE EQUIPO ELECTRÓNICO',
                              'Secundaria 1 - 4651 - VENTA AL POR MAYOR DE COMPUTADORAS']),
        'comprobantes': table(['FACTURA', 'BOLETA DE VENTA']),
        'sist_elec': table(['FACTURA PORTAL DESDE 10/01/2018']),
        'emisor': p('10/01/2018'),
        'electronicos': p('FACTURA (desde 10/01/2018),BOLETA (desde 07/06/2018)'),
        'ple': p('-'),
        'padrones': p('NINGUNO'),
    }
    parts.update(over)
    rows = [
        ('Número de RUC:', 'cabecera'), ('Tipo Contribuyente:', 'tipo'), ('Nombre Comercial:', 'comercial'),
        ('Fecha de Inscripción:', 'inscripcion'), ('Fecha de Inicio de Actividades:', 'inicio'),
        ('Estado del Contribuyente:', 'estado'), ('Condición del Contribuyente:', 'condicion'),
        ('Domicilio Fiscal:', 'domicilio'), ('Sistema Emisión de Comprobante:', 'sist_emision'),
        ('Actividad Comercio Exterior:', 'comext'), ('Sistema Contabilidad:', 'contab'),
        ('Actividad(es) Económica(s):', 'actividades'),
        ('Comprobantes de Pago c/aut. de impresión (F. 806 u 816):', 'comprobantes'),
        ('Sistema de Emisión Electrónica:', 'sist_elec'), ('Emisor electrónico desde:', 'emisor'),
        ('Comprobantes Electrónicos:', 'electronicos'), ('Afiliado al PLE desde:', 'ple'), ('Padrones:', 'padrones'),
    ]
    body = ''
    for label, key in rows:
        if parts.get(key) is None:  # el campo no existe en esta ficha
            continue
        if key == 'cabecera':
            body += ('<div class="list-group-item"><div class="row"><div class="col-sm-5">'
                     f'<h4 class="list-group-item-heading">{label}</h4></div><div class="col-sm-7">{parts[key]}</div></div></div>')
        else:
            body += item(label, parts[key])
    return ('<!doctype html><html><head><meta charset="utf-8"><title>SUNAT - Consulta RUC</title>'
            '<script>var x = "Estado del Contribuyente:";</script></head><body><h1>Consulta RUC</h1>'
            '<div class="panel-heading">Resultado de la Búsqueda</div><div class="list-group">' + body +
            '</div><input type="hidden" value="x"> Razón Social: eeee <!-- c --> Fecha consulta: 25/10/2026 7:22 '
            '<a>Volver</a><a>Información Histórica</a></body></html>')


class ParseTests(unittest.TestCase):
    def test_complete_active_company(self):
        f = pf.parse_ficha(ficha(), expected_ruc=mk(1))
        self.assertEqual(f['ruc'], mk(1))
        self.assertEqual(f['razon_social'], 'EMPRESA DE PRUEBA S.A.C.')
        self.assertEqual(f['tipo_contribuyente'], 'SOCIEDAD ANONIMA CERRADA')
        self.assertEqual(f['forma_societaria'], 'SAC')
        self.assertEqual((f['fecha_inscripcion'], f['fecha_inicio_actividades']), ('2015-03-12', '2015-03-12'))
        self.assertEqual((f['estado'], f['condicion']), ('ACTIVO', 'HABIDO'))
        self.assertIsNone(f['fecha_baja'])
        self.assertTrue(f['es_importador'])
        self.assertEqual(f['comercio_exterior'], ['IMPORTADOR', 'EXPORTADOR'])
        self.assertEqual(f['actividad_principal'], '4652')
        self.assertEqual([(a['kind'], a['position'], a['ciiu_code']) for a in f['actividades']],
                         [('PRINCIPAL', 0, '4652'), ('SECUNDARIA', 1, '4651')])
        self.assertEqual(f['actividades'][0]['description'], 'VENTA AL POR MAYOR DE EQUIPO ELECTRÓNICO')
        self.assertEqual(f['comprobantes_autorizados'], ['FACTURA', 'BOLETA DE VENTA'])
        self.assertEqual(f['emisor_electronico_desde'], '2018-01-10')
        self.assertEqual(f['comprobantes_electronicos'],
                         [{'tipo': 'FACTURA', 'desde': '2018-01-10'}, {'tipo': 'BOLETA', 'desde': '2018-06-07'}])
        self.assertEqual(f['padrones'], [])
        self.assertEqual(f['fecha_consulta'], '2026-10-25T07:22')
        self.assertAlmostEqual(pf.antiguedad_anios(f), 11.6, places=1)

    def test_baja_with_inline_date(self):
        estado = '<p class="list-group-item-text">BAJA DE OFICIO\n\t<br>\n\tFecha de Baja:\n\n\t   31/10/2024\n</p>'
        f = pf.parse_ficha(ficha(estado=estado))
        self.assertEqual(f['estado'], 'BAJA DE OFICIO')
        self.assertEqual(f['fecha_baja'], '2024-10-31')

    def test_sin_actividad_is_not_importer(self):
        f = pf.parse_ficha(ficha(comext=p('SIN ACTIVIDAD')))
        self.assertFalse(f['es_importador'])
        self.assertEqual(f['comercio_exterior'], ['SIN ACTIVIDAD'])

    def test_name_quotes_and_entities(self):
        f = pf.parse_ficha(ficha(ruc=mk(2), cabecera=f'<h4>{mk(2)} - " EMPRESA &amp; CIA E.I.R.L "</h4>'))
        self.assertEqual(f['razon_social'], 'EMPRESA & CIA E.I.R.L')

    def test_dash_means_empty(self):
        f = pf.parse_ficha(ficha(domicilio=p('-'), comercial=p('-')))
        self.assertIsNone(f['domicilio_fiscal'])
        self.assertIsNone(f['nombre_comercial'])

    def test_missing_activities_section_is_a_parse_error(self):  # AC-07: la página cambió o está rota; no se guardan datos parciales
        with self.assertRaises(pf.ParseError) as cm:
            pf.parse_ficha(ficha(actividades=None))
        self.assertTrue(any('actividades' in m for m in cm.exception.missing))

    def test_empty_activities_section_is_a_valid_record(self):  # persona natural sin negocio
        f = pf.parse_ficha(ficha(actividades=table(['-'])))
        self.assertIsNone(f['actividad_principal'])
        self.assertTrue(f['sin_actividad_principal'])
        self.assertEqual(f['actividades'], [])

    def test_five_digit_ciiu_codes_are_accepted(self):
        f = pf.parse_ficha(ficha(actividades=table(['Principal    - 52319 - VENTA AL POR MENOR DE OTROS PRODUCTOS'])))
        self.assertEqual(f['actividad_principal'], '52319')

    def test_natural_person_document_is_not_stored(self):
        f = pf.parse_ficha(ficha(tipo=p('PERSONA NATURAL CON NEGOCIO') + item('Tipo de Documento:', p('DNI 12345678 - PEREZ GOMEZ, JUAN'))))
        self.assertEqual(f['tipo_contribuyente'], 'PERSONA NATURAL CON NEGOCIO')
        self.assertEqual(f['forma_societaria'], 'NATURAL')
        self.assertEqual(f['tipo_documento'], 'DNI')
        self.assertNotIn('12345678', repr(f))
        self.assertNotIn('PEREZ', repr(f))

    def test_missing_estado_is_a_parse_error(self):
        with self.assertRaises(pf.ParseError) as cm:
            pf.parse_ficha(ficha(estado=None))
        self.assertIn('estado', cm.exception.missing)

    def test_invalid_check_digit_is_a_parse_error(self):
        bad = mk(1)[:-1] + str((int(mk(1)[-1]) + 1) % 10)
        with self.assertRaises(pf.ParseError) as cm:
            pf.parse_ficha(ficha(ruc=bad))
        self.assertTrue(any('dígito verificador' in m for m in cm.exception.missing))

    def test_ruc_mismatch_is_a_parse_error(self):
        with self.assertRaises(pf.ParseError):
            pf.parse_ficha(ficha(ruc=mk(1)), expected_ruc=mk(2))

    def test_invalid_optional_date_becomes_none_but_required_date_fails(self):
        self.assertIsNone(pf.parse_ficha(ficha(inicio=p('31/02/2015')))['fecha_inicio_actividades'])
        with self.assertRaises(pf.ParseError):
            pf.parse_ficha(ficha(inscripcion=p('no es fecha')))

    def test_page_without_the_record_at_all(self):
        with self.assertRaises(pf.ParseError):
            pf.parse_ficha('<html><body><p>Servicio en mantenimiento</p></body></html>')

    def test_forma_societaria(self):
        casos = {'SOCIEDAD ANONIMA CERRADA': 'SAC', 'SOCIEDAD ANONIMA': 'SA', 'EMPRESA INDIVIDUAL DE RESP. LTDA': 'EIRL',
                 'SOC.COM.RESPONS. LTDA': 'SRL', 'SOCIEDAD COMERCIAL DE RESPONSABILIDAD LIMITADA': 'SRL',
                 'PERSONA NATURAL CON NEGOCIO': 'NATURAL', 'SUCURSALES O AG. DE EMP. EXTRANJ.': 'SUCURSAL',
                 'UNIVERS. CENTROS EDUCAT. Y CULT.': 'OTRA', 'ASOCIACION': 'OTRA', None: 'OTRA'}
        for tipo, esperado in casos.items():
            self.assertEqual(pf.forma_societaria(tipo), esperado, tipo)


class CliTests(unittest.TestCase):
    def test_folder_with_good_and_broken_pages(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / f'{mk(1)}.html').write_text(ficha(ruc=mk(1)), encoding='utf-8')
            (d / f'{mk(2)}.html').write_text(ficha(ruc=mk(2), actividades=None), encoding='utf-8')
            (d / 'notas.html').write_text('x', encoding='utf-8')  # no es una ficha: se ignora
            out = d / 'salida' / 'f.csv'
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = pf.main([str(d), '--csv', str(out)])
            self.assertEqual(code, 1)
            self.assertIn('válidas: 1', buf.getvalue())
            self.assertIn('con error: 1', buf.getvalue())
            raw = out.read_bytes()
            self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
            rows = raw.decode('utf-8-sig').splitlines()
            self.assertEqual(len(rows), 2)  # cabecera + la ficha buena; la rota no se escribe
            self.assertIn('4652', rows[1])


REAL = pathlib.Path(__file__).resolve().parents[2] / 'data' / 'raw' / 'consulta_ruc' / '2026-10-25'


@unittest.skipUnless(REAL.exists() and any(REAL.glob('[0-9]' * 11 + '.html')), 'no hay fichas reales en data/ (normal fuera de tu equipo)')
class RealPagesTests(unittest.TestCase):
    def test_every_real_page_parses(self):
        files = [f for f in REAL.glob('*.html') if re.fullmatch(r'\d{11}', f.stem)]
        errores = []
        for f in files:
            try:
                pf.parse_ficha(f.read_text(encoding='utf-8', errors='replace'), expected_ruc=f.stem)
            except pf.ParseError as e:
                errores.append((f.stem[:3] + '…' + f.stem[-2:], str(e)))
        self.assertEqual(errores, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
