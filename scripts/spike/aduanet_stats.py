import sys, re, html, collections, datetime, pathlib

src, out = sys.argv[1], sys.argv[2]
raw = open(src, 'rb').read()
text = raw.decode('cp1252', errors='replace')
repl = text.count('�')
print(f"Archivo: {len(raw):,} bytes · decodificado como cp1252 · caracteres no representables: {repl}")

row_re = re.compile(r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', re.S | re.I)


def clean(x):
    x = re.sub(r'<[^>]+>', ' ', x)
    x = html.unescape(x).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', x).strip()


def mask(x):
    return re.sub(r'\d', '9', re.sub(r'[A-Za-zÁÉÍÓÚÑáéíóúñÀ-ÿ]', 'X', x))


def ruc_ok(r):
    if len(r) != 11 or not r.isdigit():
        return False
    w = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    d = 11 - (sum(int(r[i]) * w[i] for i in range(10)) % 11)
    d = {10: 0, 11: 1}.get(d, d)
    return d == int(r[10])


total_tr = len(re.findall(r'<tr\b', text, re.I))
rows = []
other_shapes = collections.Counter()
for m in row_re.finditer(text):
    a, b, c = clean(m.group(1)), clean(m.group(2)), clean(m.group(3))
    if re.fullmatch(r'\d{11}', a):
        rows.append((a, b, c))
    else:
        other_shapes[(mask(a)[:30], mask(b)[:20], mask(c)[:20])] += 1

print(f"\n<tr> totales en el archivo: {total_tr:,}")
print(f"Filas de datos (3 celdas, RUC de 11 dígitos): {len(rows):,}")
print(f"Filas de 3 celdas que NO son de datos (encabezados y similares): {sum(other_shapes.values()):,}")
for shp, n in other_shapes.most_common(5):
    print("   ", n, shp)

# duplicados
by_ruc = collections.defaultdict(list)
for i, (r, n, d) in enumerate(rows):
    by_ruc[r].append((n, d))
uniq = len(by_ruc)
mult = collections.Counter(len(v) for v in by_ruc.values())
print(f"\nRUC únicos: {uniq:,}")
print(f"Filas sobrantes por duplicados: {len(rows) - uniq:,} ({(len(rows)-uniq)/len(rows):.1%})")
print("RUC según nº de apariciones:", {k: mult[k] for k in sorted(mult)})
diff_names = sum(1 for v in by_ruc.values() if len({re.sub(r'[\"\s]', '', n).upper() for n, _ in v}) > 1)
diff_dates = sum(1 for v in by_ruc.values() if len({d for _, d in v}) > 1)
print(f"RUC repetidos con nombres distintos (ignorando comillas y espacios): {diff_names:,} · con fechas distintas: {diff_dates:,}")

# validación RUC
prefix = collections.Counter(r[:2] for r in by_ruc)
bad = [r for r in by_ruc if not ruc_ok(r)]
print(f"\nPrefijos de RUC únicos: {dict(prefix.most_common())}")
print(f"RUC únicos con dígito verificador inválido: {len(bad):,}")
if bad:
    print("   prefijos de los inválidos:", dict(collections.Counter(r[:2] for r in bad)))
    print("   formas:", dict(collections.Counter(mask(r) for r in bad).most_common(3)))
print("Prefijo no reconocido (distinto de 10, 15, 16, 17, 20):", sum(v for k, v in prefix.items() if k not in ('10', '15', '16', '17', '20')))

# nombres
names = [n for _, n, _ in rows]
print(f"\nNombres vacíos: {sum(1 for n in names if not n):,}")
print(f"Nombres que empiezan o terminan con comillas: {sum(1 for n in names if n.startswith(chr(34)) or n.endswith(chr(34))):,}")
print(f"Nombres idénticos al propio RUC: {sum(1 for r, n, _ in rows if n == r):,}")
print(f"Nombres con caracteres no ASCII: {sum(1 for n in names if any(ord(ch) > 127 for ch in n)):,}")
print(f"Nombre más largo: {max(len(n) for n in names)} caracteres")

# fechas
dates = []
bad_dates = 0
for r, n, d in rows:
    try:
        dates.append(datetime.datetime.strptime(d, '%d/%m/%Y').date())
    except ValueError:
        bad_dates += 1
print(f"\nFechas ULT.ACT. con formato inválido: {bad_dates:,}")
if dates:
    print(f"Rango: {min(dates)} a {max(dates)}")
    ref = datetime.date(2026, 10, 24)
    print("Fechas futuras (> 24/10/2026):", sum(1 for d in dates if d > ref))
    years = collections.Counter(d.year for d in dates)
    print("Filas por año:", {y: years[y] for y in sorted(years)})

# última actualización por RUC (la más reciente)
last = {}
for r, v in by_ruc.items():
    ds = []
    for _, d in v:
        try:
            ds.append(datetime.datetime.strptime(d, '%d/%m/%Y').date())
        except ValueError:
            pass
    last[r] = max(ds) if ds else None
ref = datetime.date(2026, 10, 24)
le2 = sum(1 for d in last.values() if d and (ref - d).days <= 2 * 365)
le5 = sum(1 for d in last.values() if d and (ref - d).days <= 5 * 365)
print(f"\nRUC únicos con última actualización ≤ 2 años: {le2:,} ({le2/uniq:.1%}) · ≤ 5 años: {le5:,} ({le5/uniq:.1%})")

# orden
key = lambda n: re.sub(r'[\"\s]', '', n).upper()
desc = sum(1 for i in range(1, len(rows)) if key(rows[i][1]) < key(rows[i - 1][1]))
print(f"Descensos de orden alfabético entre filas consecutivas: {desc:,} de {len(rows)-1:,}")

# salida sin nombres
p = pathlib.Path(out)
p.parent.mkdir(parents=True, exist_ok=True)
with open(p, 'w', encoding='utf-8') as f:
    f.write('ruc\tkind\taduanet_last_update\tappearances\n')
    for r in sorted(by_ruc):
        kind = {'20': 'JURIDICA', '10': 'NATURAL'}.get(r[:2], 'OTRO')
        f.write(f"{r}\t{kind}\t{last[r].isoformat() if last[r] else ''}\t{len(by_ruc[r])}\n")
print(f"\nGuardé {uniq:,} RUC únicos (sin nombres) en {p}")
