import sys, zipfile, re, time, json, collections

path = sys.argv[1]
t0 = time.time()
z = zipfile.ZipFile(path)
infos = z.infolist()
print("== Entradas del ZIP ==")
for i in infos:
    print(f"  {i.filename}  comprimido={i.compress_size:,}  descomprimido={i.file_size:,}  método={i.compress_type}")
if len(infos) != 1:
    print("AVISO: se esperaba 1 entrada")
info = infos[0]
if info.file_size > 6 * 1024**3:
    sys.exit("Descomprimido demasiado grande, se aborta")

def mask(s):
    s = re.sub(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", "X", s)
    return re.sub(r"\d", "9", s)

with z.open(info) as f:
    head = f.read(4096)
# codificación
enc_guess = "utf-8"
try:
    head.decode("utf-8")
except UnicodeDecodeError:
    enc_guess = "latin-1 (no es UTF-8 válido)"
print("\n== Codificación de las primeras 4 KB ==", enc_guess)
print("BOM UTF-8:", head.startswith(b"\xef\xbb\xbf"))
print("Terminador de línea CRLF:", b"\r\n" in head)

lines_head = head.decode("latin-1").splitlines()
header = lines_head[0]
print("\n== Primera línea (cabecera) ==")
print(header)
delim = max(["|", ",", "\t", ";"], key=lambda d: header.count(d))
cols = [c.strip() for c in header.split(delim)]
print(f"Delimitador detectado: {delim!r} · columnas: {len(cols)}")
for n, c in enumerate(cols):
    print(f"  [{n}] {c}")
print("\n== Forma de las 3 primeras filas de datos (enmascarada) ==")
for l in lines_head[1:4]:
    print("  ", mask(l)[:200])

def find(*keys):
    for n, c in enumerate(cols):
        u = c.upper()
        if all(k in u for k in keys):
            return n
    return None

i_ruc = 0
i_est = find("ESTADO")
i_con = find("CONDICI")
i_ubi = find("UBIGEO")
print(f"\nÍndices: RUC={i_ruc} estado={i_est} condición={i_con} ubigeo={i_ubi}")

total = 0
bad_cols = 0
bad_utf8 = 0
ruc_bad = 0
prefix = collections.Counter()
estado = collections.Counter()
condicion = collections.Counter()
est_cond_20 = collections.Counter()
ubigeo_len = collections.Counter()
maxlen = 0
nfields = len(cols)
first = True
with z.open(info) as f:
    for raw in f:
        if first:
            first = False
            continue
        total += 1
        if len(raw) > maxlen:
            maxlen = len(raw)
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            bad_utf8 += 1
        s = raw.decode("latin-1").rstrip("\r\n")
        parts = s.split(delim)
        if len(parts) != nfields:
            bad_cols += 1
            continue
        ruc = parts[i_ruc].strip()
        if not (len(ruc) == 11 and ruc.isdigit()):
            ruc_bad += 1
        prefix[ruc[:2]] += 1
        e = parts[i_est].strip() if i_est is not None else ""
        c = parts[i_con].strip() if i_con is not None else ""
        estado[e] += 1
        condicion[c] += 1
        if ruc.startswith("20"):
            est_cond_20[(e, c)] += 1
        if i_ubi is not None:
            ubigeo_len[len(parts[i_ubi].strip())] += 1

print(f"\n== Totales ==")
print(f"Filas de datos: {total:,}")
print(f"Filas con nº de columnas distinto a la cabecera: {bad_cols:,}")
print(f"Filas que no son UTF-8 válido: {bad_utf8:,} ({bad_utf8/max(total,1):.1%})")
print(f"RUC que no tienen 11 dígitos: {ruc_bad:,}")
print(f"Línea más larga: {maxlen:,} bytes")
print("\nPrefijos de RUC:", dict(prefix.most_common(8)))
print("\n== Estado del contribuyente (todas las filas) ==")
for k, v in estado.most_common():
    print(f"  {k!r:45} {v:>12,}")
print("\n== Condición de domicilio (todas las filas) ==")
for k, v in condicion.most_common():
    print(f"  {k!r:30} {v:>12,}")
print("\n== Estado × Condición solo en RUC 20 (personas jurídicas), top 12 ==")
for (e, c), v in est_cond_20.most_common(12):
    print(f"  {e!r:30} {c!r:20} {v:>10,}")
print("\nLongitud de ubigeo:", dict(ubigeo_len))
print(f"\nTiempo: {time.time()-t0:.0f} s")
