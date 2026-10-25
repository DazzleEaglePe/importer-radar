"""SP-06: arma la muestra de 20 RUC variados para las consultas manuales de RUC.

Uso:
    python3 -I pick_sp06_sample.py IMPORTADORES.csv SALIDA.csv

Entrada: el CSV que genera export_h1_csv.py (importadores ACTIVO + HABIDO).
Salida: 20 filas (18 empresas y 2 personas naturales) con la columna «para_probar», el nombre de archivo
sugerido para guardar cada página y dos columnas vacías para que anotes si SUNAT pidió verificación.

La elección es reproducible (semilla fija) y cubre: S.A.C., S.A., E.I.R.L., S.R.L., sucursal de empresa
extranjera y otras formas; con y sin palabras clave en el nombre; Lima, Callao y provincias.
"""
import csv
import random
import re
import sys
import unicodedata

src, out = sys.argv[1:3]
rng = random.Random(20261025)
FECHA = '2026-10-25'


def norm(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper()
    return ' ' + re.sub(r'[.\s,&\-]+', ' ', s).strip() + ' '


def forma(name):
    n = norm(name)
    if ' SUCURSAL ' in n:
        return 'Sucursal'
    if ' SAC ' in n or ' S A C ' in n or ' SOCIEDAD ANONIMA CERRADA ' in n:
        return 'S.A.C.'
    if ' SA ' in n or ' S A ' in n or ' SOCIEDAD ANONIMA ' in n:
        return 'S.A.'
    if ' EIRL ' in n or ' E I R L ' in n or ' EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA ' in n:
        return 'E.I.R.L.'
    if ' SRL ' in n or ' S R L ' in n or ' SRLTDA ' in n or ' S R LTDA ' in n or ' SCRL ' in n or ' S C R L ' in n:
        return 'S.R.L.'
    return 'Otra'


rows = list(csv.DictReader(open(src, encoding='utf-8-sig', newline='')))
companies = []
naturals = []
for r in rows:
    r['forma'] = forma(r['razon_social']) if r['tipo'] != 'Persona natural' else 'Persona natural'
    r['lugar'] = 'Lima' if r['departamento'] == 'Lima' else 'Callao' if r['departamento'] == 'Callao' else (
        'Sin dato' if r['departamento'] == '(sin dato)' else 'Provincia')
    (naturals if r['tipo'] == 'Persona natural' else companies).append(r)
rng.shuffle(companies)
rng.shuffle(naturals)

# (forma, con_palabra_clave: True/False/None, lugar: 'Lima'/'Callao'/'Provincia'/None)
SPECS = [
    ('S.A.C.', True, 'Lima'), ('S.A.C.', True, 'Lima'), ('S.A.C.', False, 'Lima'),
    ('S.A.C.', False, 'Provincia'), ('S.A.C.', None, 'Callao'),
    ('S.A.', True, 'Lima'), ('S.A.', True, None), ('S.A.', False, 'Lima'), ('S.A.', False, 'Provincia'),
    ('E.I.R.L.', True, None), ('E.I.R.L.', False, 'Lima'), ('E.I.R.L.', False, 'Provincia'), ('E.I.R.L.', None, 'Provincia'),
    ('S.R.L.', False, 'Lima'), ('S.R.L.', False, 'Provincia'),
    ('Sucursal', None, 'Lima'),
    ('Otra', False, None), ('Otra', True, None),
]

chosen, used_dep = [], set()
for fm, kw, lugar in SPECS:
    def ok(r, strict_place=True, strict_dep=True):
        if r in chosen or r['forma'] != fm:
            return False
        if kw is not None and bool(r['palabras_clave']) != kw:
            return False
        if strict_place and lugar is not None and r['lugar'] != lugar:
            return False
        if strict_dep and lugar == 'Provincia' and r['departamento'] in used_dep:
            return False
        return True
    pick = next((r for r in companies if ok(r)), None) \
        or next((r for r in companies if ok(r, strict_dep=False)), None) \
        or next((r for r in companies if ok(r, strict_place=False, strict_dep=False)), None)
    if pick is None:
        print(f'AVISO: no encontré candidato para {fm} / palabra clave={kw} / lugar={lugar}')
        continue
    chosen.append(pick)
    used_dep.add(pick['departamento'])

chosen += naturals[:2]


def why(r):
    if r['forma'] == 'Persona natural':
        return 'Persona natural: ficha con datos limitados (sin domicilio publicado)'
    kw = f"con palabras clave ({r['palabras_clave']})" if r['palabras_clave'] else 'sin palabras clave'
    base = {'Sucursal': 'Sucursal de empresa extranjera: pueden cambiar los campos de la ficha',
            'Otra': 'Otra forma (asociación, cooperativa, etc.)'}.get(r['forma'], f"{r['forma']}")
    return f"{base} · {kw} · {r['departamento']}"


cols = ['n', 'ruc', 'razon_social', 'forma', 'departamento', 'prioridad', 'palabras_clave', 'para_probar',
        'archivo_sugerido', 'pidio_verificacion', 'observaciones']
with open(out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for i, r in enumerate(chosen, 1):
        w.writerow({
            'n': i, 'ruc': r['ruc'], 'razon_social': r['razon_social'], 'forma': r['forma'],
            'departamento': r['departamento'], 'prioridad': r['prioridad'], 'palabras_clave': r['palabras_clave'],
            'para_probar': why(r), 'archivo_sugerido': f"data/raw/consulta_ruc/{FECHA}/{r['ruc']}.html",
            'pidio_verificacion': '', 'observaciones': '',
        })
print(f'Escribí {len(chosen)} filas en {out}')
