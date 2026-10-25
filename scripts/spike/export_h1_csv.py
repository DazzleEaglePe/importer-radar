"""Hito H1 (versión del spike): exporta a CSV los importadores ACTIVO + HABIDO de la lista de Aduanet.

Uso:
    python3 -I export_h1_csv.py LISTA.html ELEGIBLES.tsv SALIDA.csv

Entradas:
    LISTA.html     HTML original de Aduanet (windows-1252).
    ELEGIBLES.tsv  Salida de padron_cross.py: ruc, tipo, estado, condición y ubigeo de los ACTIVO + HABIDO.

Reglas:
    - razón social: la de la fila con la fecha más reciente (desempate: el nombre más largo),
      sin las comillas que envuelven a todo el nombre.
    - departamento: dos primeros dígitos del ubigeo (tabla del INEI). Sin ubigeo: «(sin dato)».
    - prioridad (0 a 100): +40 si es persona jurídica, +30 si el ubigeo es de Lima o Callao,
      +10 por cada palabra clave distinta en el nombre (máximo +30). Ordena la cola de consultas;
      nunca excluye a nadie (docs/02 RF-FIL-03).
"""
import csv
import datetime
import html
import re
import sys
import unicodedata

html_path, elig_path, out_path = sys.argv[1:4]

DEPARTAMENTOS = {
    '01': 'Amazonas', '02': 'Áncash', '03': 'Apurímac', '04': 'Arequipa', '05': 'Ayacucho',
    '06': 'Cajamarca', '07': 'Callao', '08': 'Cusco', '09': 'Huancavelica', '10': 'Huánuco',
    '11': 'Ica', '12': 'Junín', '13': 'La Libertad', '14': 'Lambayeque', '15': 'Lima',
    '16': 'Loreto', '17': 'Madre de Dios', '18': 'Moquegua', '19': 'Pasco', '20': 'Piura',
    '21': 'Puno', '22': 'San Martín', '23': 'Tacna', '24': 'Tumbes', '25': 'Ucayali',
}
TIPOS = {'JURIDICA': 'Persona jurídica', 'NATURAL': 'Persona natural', 'OTRO': 'Otro (prefijo 15 o 17)'}

# Palabra clave -> función que decide si un token del nombre la cumple.
KEYWORDS = {
    'TECH': lambda t: t == 'TECH' or t.startswith('TECHNO'),
    'TECNOLOG': lambda t: t.startswith('TECNOLOG'),
    'CELULAR': lambda t: t.startswith('CELULAR'),
    'CELL': lambda t: t in ('CELL', 'CELLS'),
    'PHONE': lambda t: t.endswith('PHONE') or t.endswith('PHONES'),
    'TELEFON': lambda t: t.startswith('TELEFON'),
    'TELECOM': lambda t: t.startswith('TELECOM'),
    'COMPUT': lambda t: t.startswith('COMPUT'),
    'LAPTOP': lambda t: t.startswith('LAPTOP'),
    'DIGITAL': lambda t: t.startswith('DIGITAL'),
    'ELECTRON': lambda t: t.startswith('ELECTRON'),
    'MOBILE': lambda t: t.startswith('MOBILE'),
    'MOVIL': lambda t: t.startswith('MOVIL'),
    'INFORMAT': lambda t: t.startswith('INFORMAT'),
}


def clean(x):
    x = re.sub(r'<[^>]+>', ' ', x)
    x = html.unescape(x).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', x).strip()


def tidy_name(n):
    n = n.strip()
    if n.count('"') == 2 and n.startswith('"') and n.endswith('"'):
        n = n[1:-1]
    return re.sub(r'\s+', ' ', n).strip()


def tokens(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper()
    return re.findall(r'[A-Z0-9]+', s)


text = open(html_path, 'rb').read().decode('cp1252', errors='replace')
row_re = re.compile(r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', re.S | re.I)
best = {}
for m in row_re.finditer(text):
    ruc, name, date = clean(m.group(1)), tidy_name(clean(m.group(2))), clean(m.group(3))
    if not re.fullmatch(r'\d{11}', ruc):
        continue
    try:
        d = datetime.datetime.strptime(date, '%d/%m/%Y').date()
    except ValueError:
        d = datetime.date.min
    key = (d, len(name))
    if ruc not in best or key > best[ruc][0]:
        best[ruc] = (key, name)

out_rows = []
with open(elig_path, encoding='utf-8') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        ruc = r['ruc']
        name = best[ruc][1]
        ub = r['ubigeo']
        dep = DEPARTAMENTOS.get(ub[:2], '(sin dato)') if len(ub) == 6 else '(sin dato)'
        toks = tokens(name)
        hits = [k for k, fn in KEYWORDS.items() if any(fn(t) for t in toks)]
        prio = (40 if r['kind'] == 'JURIDICA' else 0) + (30 if ub[:2] in ('15', '07') and len(ub) == 6 else 0) + min(30, 10 * len(hits))
        out_rows.append({
            'ruc': ruc,
            'razon_social': name,
            'tipo': TIPOS.get(r['kind'], r['kind']),
            'estado': r['estado'],
            'condicion': r['condicion'],
            'departamento': dep,
            'ubigeo': ub,
            'prioridad': prio,
            'palabras_clave': ' '.join(hits),
        })

out_rows.sort(key=lambda x: (-x['prioridad'], x['razon_social']))
cols = ['ruc', 'razon_social', 'tipo', 'estado', 'condicion', 'departamento', 'ubigeo', 'prioridad', 'palabras_clave']
with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(out_rows)
print(f'Escribí {len(out_rows):,} filas en {out_path}')
