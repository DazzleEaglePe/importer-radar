import sys, zipfile, collections, datetime, csv

zip_path, rucs_tsv, out_tsv = sys.argv[1], sys.argv[2], sys.argv[3]

ours = {}
with open(rucs_tsv, encoding='utf-8') as f:
    for row in csv.DictReader(f, delimiter='\t'):
        ours[row['ruc']] = (row['kind'], row['aduanet_last_update'], int(row['appearances']))
print(f"RUC únicos de la lista de Aduanet: {len(ours):,}")

found = {}
z = zipfile.ZipFile(zip_path)
info = z.infolist()[0]
n_rows = 0
with z.open(info) as f:
    first = True
    for raw in f:
        if first:
            first = False
            continue
        n_rows += 1
        parts = raw.decode('latin-1').rstrip('\r\n').split('|')
        if len(parts) != 16:
            continue
        r = parts[0].strip()
        if r in ours:
            found[r] = (parts[2].strip(), parts[3].strip(), parts[4].strip())
print(f"Filas del padrón leídas: {n_rows:,}")

kinds = collections.Counter(v[0] for v in ours.values())
print(f"\nPor tipo en la lista: {dict(kinds)}")
matched = len(found)
print(f"RUC de la lista encontrados en el padrón: {matched:,} ({matched/len(ours):.1%}) · NO encontrados: {len(ours)-matched:,}")
miss_kind = collections.Counter(ours[r][0] for r in ours if r not in found)
print("No encontrados por tipo:", dict(miss_kind))

est = collections.Counter(v[0] for v in found.values())
print("\n== Estado entre los encontrados ==")
for k, v in est.most_common():
    print(f"  {k!r:28} {v:>8,}  ({v/matched:.1%})")
print("\n== Condición entre los encontrados ==")
for k, v in collections.Counter(v[1] for v in found.values()).most_common(8):
    print(f"  {k!r:28} {v:>8,}")

combo = collections.Counter()
for r, (e, c, u) in found.items():
    combo[(ours[r][0], e, c)] += 1
print("\n== Tipo × Estado × Condición (top 10) ==")
for (k, e, c), v in combo.most_common(10):
    print(f"  {k:9} {e!r:24} {c!r:14} {v:>8,}")

elig = [r for r, (e, c, u) in found.items() if e == 'ACTIVO' and c == 'HABIDO']
print(f"\n*** ACTIVO + HABIDO: {len(elig):,} de {len(ours):,} RUC únicos de la lista ({len(elig)/len(ours):.1%}) ***")
ek = collections.Counter(ours[r][0] for r in elig)
print("   por tipo:", dict(ek))
ref = datetime.date(2026, 10, 24)
d2 = d5 = dold = 0
for r in elig:
    d = ours[r][1]
    if not d:
        continue
    age = (ref - datetime.date.fromisoformat(d)).days
    if age <= 730: d2 += 1
    elif age <= 1825: d5 += 1
    else: dold += 1
print(f"   última actualización en Aduanet: ≤2 años {d2:,} · 2 a 5 años {d5:,} · >5 años {dold:,}")
ub = collections.Counter()
for r in elig:
    u = found[r][2]
    ub['sin ubigeo' if len(u) != 6 else u[:2]] += 1
print("   ubigeo (2 primeros dígitos; 15=Lima, 07=Callao):", dict(ub.most_common(8)))
lc = ub.get('15', 0) + ub.get('07', 0)
print(f"   Lima + Callao: {lc:,} ({lc/len(elig):.1%} de los elegibles)")

# lista de elegibles sin nombres
with open(out_tsv, 'w', encoding='utf-8') as f:
    f.write('ruc\tkind\taduanet_last_update\tappearances\testado\tcondicion\tubigeo\n')
    for r in sorted(elig):
        k, d, a = ours[r]
        e, c, u = found[r]
        f.write(f"{r}\t{k}\t{d}\t{a}\t{e}\t{c}\t{u if len(u) == 6 else ''}\n")
print(f"\nGuardé los {len(elig):,} elegibles (sin nombres) en {out_tsv}")
