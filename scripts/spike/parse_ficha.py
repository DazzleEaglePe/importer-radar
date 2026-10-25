"""Parser de las fichas de la consulta RUC guardadas por lookup_fetch.py (prototipo; docs/05 §5, RF-CON-02 y RF-CON-09).

Uso:
    python3 -I parse_ficha.py CARPETA_DE_FICHAS [--csv SALIDA.csv]

Lee cada `<ruc>.html`, extrae los campos y VALIDA que estén los obligatorios: si falta alguno, esa ficha
se reporta como error y no se escribe como válida (nunca se guardan datos parciales como buenos).

Método: se saca el texto de la página en orden y se agrupan las líneas bajo cada etiqueta conocida
(«Número de RUC:», «Estado del Contribuyente:», etc.). Así no depende de las clases CSS ni de la maqueta.
Compatible con Python 3.9, solo biblioteca estándar.
"""
import csv
import datetime
import html as htmllib
import pathlib
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from typing import Dict, List, Optional

L_RUC = 'Número de RUC:'
L_TIPO = 'Tipo Contribuyente:'
L_TIPO_DOC = 'Tipo de Documento:'  # personas naturales: «DNI 12345678 - NOMBRE». Dato personal: solo se guarda el tipo de documento
L_COMERCIAL = 'Nombre Comercial:'
L_INSCRIPCION = 'Fecha de Inscripción:'
L_INICIO = 'Fecha de Inicio de Actividades:'
L_ESTADO = 'Estado del Contribuyente:'
L_BAJA = 'Fecha de Baja:'
L_CONDICION = 'Condición del Contribuyente:'
L_DOMICILIO = 'Domicilio Fiscal:'
L_SIST_EMISION = 'Sistema Emisión de Comprobante:'
L_COMEXT = 'Actividad Comercio Exterior:'
L_CONTAB = 'Sistema Contabilidad:'
L_ACTIVIDADES = 'Actividad(es) Económica(s):'
L_COMPROBANTES = 'Comprobantes de Pago c/aut. de impresión (F. 806 u 816):'
L_SIST_ELECTRONICO = 'Sistema de Emisión Electrónica:'
L_EMISOR_DESDE = 'Emisor electrónico desde:'
L_ELECTRONICOS = 'Comprobantes Electrónicos:'
L_PLE = 'Afiliado al PLE desde:'
L_PADRONES = 'Padrones:'

LABELS = [L_RUC, L_TIPO, L_TIPO_DOC, L_COMERCIAL, L_INSCRIPCION, L_INICIO, L_ESTADO, L_BAJA, L_CONDICION, L_DOMICILIO,
          L_SIST_EMISION, L_COMEXT, L_CONTAB, L_ACTIVIDADES, L_COMPROBANTES, L_SIST_ELECTRONICO, L_EMISOR_DESDE,
          L_ELECTRONICOS, L_PLE, L_PADRONES]
# Líneas que cierran el bloque de la última etiqueta (avisos, campos ocultos y pie).
STOPS = {'IMPORTANTE:', 'Razón Social:', 'Volver', 'Información Histórica'}
REQUIRED = ['ruc', 'razon_social', 'tipo_contribuyente', 'fecha_inscripcion', 'estado', 'condicion']

ACTIVITY_RE = re.compile(r'^(Principal|Secundaria\s*(\d+))\s*-\s*(\d{4,5})\s*-\s*(.+)$')  # algunos CIIU vienen de 5 dígitos (revisión 3)
DATE_RE = re.compile(r'^(\d{2})/(\d{2})/(\d{4})$')


class ParseError(Exception):
    def __init__(self, missing: List[str], note: str = ''):
        super().__init__(f"faltan o son inválidos: {', '.join(missing)}" + (f' ({note})' if note else ''))
        self.missing = missing


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip:
            return
        s = re.sub(r'\s+', ' ', data.replace('\xa0', ' ')).strip()
        if s:
            self.lines.append(s)


def text_lines(html_text: str) -> List[str]:
    p = _Text()
    p.feed(html_text)
    p.close()
    return p.lines


def sections(lines: List[str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    cur: Optional[str] = None
    for line in lines:
        label = next((lab for lab in LABELS if line == lab or line.startswith(lab + ' ')), None)
        if label is not None:  # la etiqueta puede traer su valor en la misma línea («Fecha de Baja: 31/10/2024»)
            cur = label
            out.setdefault(cur, [])
            rest = line[len(label):].strip()
            if rest:
                out[cur].append(rest)
            continue
        if cur is not None and (line.startswith('Fecha consulta') or any(line == s or line.startswith(s + ' ') for s in STOPS)):
            cur = None
            continue
        if cur is not None:
            out[cur].append(line)
    return out


def _one(sec: Dict[str, List[str]], label: str) -> Optional[str]:
    v = ' '.join(sec.get(label, [])).strip()
    return None if v in ('', '-') else v


def _date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = DATE_RE.match(s.strip())
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def _clean_name(n: str) -> str:
    n = n.strip()
    if n.count('"') == 2 and n.startswith('"') and n.endswith('"'):
        n = n[1:-1]
    return re.sub(r'\s+', ' ', n).strip()


def ruc_ok(r: str) -> bool:
    if len(r) != 11 or not r.isdigit():
        return False
    w = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    d = 11 - (sum(int(r[i]) * w[i] for i in range(10)) % 11)
    return {10: 0, 11: 1}.get(d, d) == int(r[10])


def forma_societaria(tipo: Optional[str]) -> str:
    t = (tipo or '').upper()
    if 'PERSONA NATURAL' in t:
        return 'NATURAL'
    if 'ANONIMA CERRADA' in t:
        return 'SAC'
    if 'ANONIMA' in t:
        return 'SA'
    if 'INDIVIDUAL' in t and 'LTDA' in t or 'E.I.R.L' in t:
        return 'EIRL'
    if 'RESPONSABILIDAD LIMITADA' in t or 'SCRL' in t or 'S.R.L' in t or ('RESPONS' in t and 'LTDA' in t):
        return 'SRL'
    if 'SUCURSAL' in t:
        return 'SUCURSAL'
    return 'OTRA'


def parse_ficha(html_text: str, expected_ruc: Optional[str] = None) -> dict:
    sec = sections(text_lines(html_text))
    f: dict = {}
    head = _one(sec, L_RUC) or ''
    m = re.match(r'^(\d{11})\s*-\s*(.*)$', head)
    f['ruc'] = m.group(1) if m else None
    f['razon_social'] = _clean_name(m.group(2)) if m and m.group(2).strip() else None
    f['tipo_contribuyente'] = _one(sec, L_TIPO)
    doc = _one(sec, L_TIPO_DOC)
    f['tipo_documento'] = doc.split()[0] if doc else None  # solo «DNI», «CE»…; nunca el número ni el nombre
    f['forma_societaria'] = forma_societaria(f['tipo_contribuyente'])
    f['nombre_comercial'] = _one(sec, L_COMERCIAL)
    f['fecha_inscripcion'] = _date(_one(sec, L_INSCRIPCION))
    f['fecha_inicio_actividades'] = _date(_one(sec, L_INICIO))
    f['estado'] = _one(sec, L_ESTADO)
    f['fecha_baja'] = _date(_one(sec, L_BAJA))
    f['condicion'] = _one(sec, L_CONDICION)
    f['domicilio_fiscal'] = _one(sec, L_DOMICILIO)
    f['sistema_emision'] = _one(sec, L_SIST_EMISION)
    ce = _one(sec, L_COMEXT)
    f['comercio_exterior_raw'] = ce
    f['comercio_exterior'] = [x.strip() for x in ce.split('/')] if ce else []
    f['es_importador'] = 'IMPORTADOR' in f['comercio_exterior']
    f['sistema_contabilidad'] = _one(sec, L_CONTAB)

    acts = []
    for line in sec.get(L_ACTIVIDADES, []):
        a = ACTIVITY_RE.match(line)
        if a:
            principal = a.group(1) == 'Principal'
            acts.append({'kind': 'PRINCIPAL' if principal else 'SECUNDARIA',
                         'position': 0 if principal else int(a.group(2)),
                         'ciiu_code': a.group(3), 'description': a.group(4).strip()})
    f['actividades'] = acts
    f['actividad_principal'] = next((a['ciiu_code'] for a in acts if a['kind'] == 'PRINCIPAL'), None)

    f['comprobantes_autorizados'] = [x for x in sec.get(L_COMPROBANTES, []) if x != '-']
    f['sistema_emision_electronica'] = [x for x in sec.get(L_SIST_ELECTRONICO, []) if x != '-']
    f['emisor_electronico_desde'] = _date(_one(sec, L_EMISOR_DESDE))
    elec = []
    for part in ' '.join(sec.get(L_ELECTRONICOS, [])).split(','):
        e = re.match(r'^\s*([A-ZÁÉÍÓÚÑ ]+?)\s*\(desde (\d{2}/\d{2}/\d{4})\)\s*$', part)
        if e:
            elec.append({'tipo': e.group(1).strip(), 'desde': _date(e.group(2))})
    f['comprobantes_electronicos'] = elec
    f['afiliado_ple_desde'] = _date(_one(sec, L_PLE))
    f['padrones'] = [x for x in sec.get(L_PADRONES, []) if x not in ('-', 'NINGUNO')]
    cons = re.search(r'Fecha consulta:\s*(\d{2}/\d{2}/\d{4})\s+(\d{1,2}):(\d{2})', ' '.join(text_lines(html_text)))
    f['fecha_consulta'] = None
    if cons:
        d = _date(cons.group(1))
        if d:
            f['fecha_consulta'] = f'{d}T{int(cons.group(2)):02d}:{cons.group(3)}'

    missing = [k for k in REQUIRED if not f.get(k)]
    if L_ACTIVIDADES not in sec:  # si la sección falta, la página cambió o está rota; si está vacía, es una ficha válida sin actividad
        missing.append('actividades (no apareció la sección)')
    f['sin_actividad_principal'] = f['actividad_principal'] is None
    if f['ruc'] and not ruc_ok(f['ruc']):
        missing.append('ruc (dígito verificador)')
    if expected_ruc and f['ruc'] and f['ruc'] != expected_ruc:
        raise ParseError(['ruc'], f'la ficha es de {f["ruc"]} y se esperaba {expected_ruc}')
    if missing:
        raise ParseError(missing)
    return f


def antiguedad_anios(f: dict) -> Optional[float]:
    if not f.get('fecha_inscripcion'):
        return None
    ref = datetime.date.fromisoformat((f.get('fecha_consulta') or datetime.date.today().isoformat())[:10])
    d = datetime.date.fromisoformat(f['fecha_inscripcion'])
    return round((ref - d).days / 365.25, 1)


CSV_COLS = ['ruc', 'razon_social', 'tipo_contribuyente', 'forma_societaria', 'fecha_inscripcion', 'antiguedad_anios',
            'estado', 'fecha_baja', 'condicion', 'comercio_exterior', 'es_importador', 'ciiu_principal',
            'ciiu_secundarias', 'n_actividades', 'emite_factura', 'emisor_electronico_desde']


def to_row(f: dict) -> dict:
    fac = 'FACTURA' in f['comprobantes_autorizados'] or any(e['tipo'].startswith('FACTURA') for e in f['comprobantes_electronicos'])
    return {'ruc': f['ruc'], 'razon_social': f['razon_social'], 'tipo_contribuyente': f['tipo_contribuyente'],
            'forma_societaria': f['forma_societaria'], 'fecha_inscripcion': f['fecha_inscripcion'],
            'antiguedad_anios': antiguedad_anios(f), 'estado': f['estado'], 'fecha_baja': f['fecha_baja'] or '',
            'condicion': f['condicion'], 'comercio_exterior': f['comercio_exterior_raw'] or '',
            'es_importador': f['es_importador'], 'ciiu_principal': f['actividad_principal'],
            'ciiu_secundarias': ' '.join(a['ciiu_code'] for a in f['actividades'] if a['kind'] == 'SECUNDARIA'),
            'n_actividades': len(f['actividades']), 'emite_factura': fac,
            'emisor_electronico_desde': f['emisor_electronico_desde'] or ''}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    csv_out = None
    if '--csv' in args:
        i = args.index('--csv')
        csv_out = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    folder = pathlib.Path(args[0])
    files = sorted(p for p in folder.glob('*.html') if re.fullmatch(r'\d{11}', p.stem))
    rows, errors = [], []
    for p in files:
        try:
            rows.append(parse_ficha(p.read_text(encoding='utf-8', errors='replace'), expected_ruc=p.stem))
        except ParseError as e:
            errors.append((p.stem, str(e)))
    print(f'Fichas leídas: {len(files)} · válidas: {len(rows)} · con error: {len(errors)}')
    for ruc, why in errors:
        print(f'  ERROR {ruc[:3]}…{ruc[-2:]}: {why}')
    if rows:
        print('\nTipo de contribuyente:', dict(Counter(r['tipo_contribuyente'] for r in rows)))
        print('Forma societaria (derivada):', dict(Counter(r['forma_societaria'] for r in rows)))
        print('Estado:', dict(Counter(r['estado'] for r in rows)), '· Condición:', dict(Counter(r['condicion'] for r in rows)))
        print('Comercio exterior:', dict(Counter(r['comercio_exterior_raw'] for r in rows)))
        print('Nº de actividades:', dict(sorted(Counter(len(r['actividades']) for r in rows).items())))
        print('CIIU principal:', dict(Counter(r['actividad_principal'] for r in rows).most_common(12)))
        print('Con emisor electrónico:', sum(1 for r in rows if r['emisor_electronico_desde']), 'de', len(rows))
    if csv_out and rows:
        out = pathlib.Path(csv_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_COLS)
            w.writeheader()
            w.writerows(to_row(r) for r in rows)
        print(f'\nEscribí {len(rows)} filas en {out}')
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
