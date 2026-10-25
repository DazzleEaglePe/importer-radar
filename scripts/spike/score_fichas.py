"""Aplica el motor de puntaje a las fichas guardadas y compara el perfil actual (v1) con la propuesta P1 (v2).

Uso:
    python3 -I score_fichas.py CARPETA_DE_FICHAS ELEGIBLES.tsv [--csv SALIDA.csv]

ELEGIBLES.tsv es el archivo de `padron_cross.py` (de ahí sale el ubigeo, que la ficha no trae).
Privacidad: nunca se muestran ni se escriben los nombres de las personas naturales ni se imprime su RUC completo.
"""
import csv
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import parse_ficha as pf  # noqa: E402
import scoring as sc  # noqa: E402


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    csv_out = None
    if '--csv' in args:
        i = args.index('--csv')
        csv_out = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        print(__doc__)
        return 2
    folder, elig = pathlib.Path(args[0]), args[1]
    ubigeo = {}
    with open(elig, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            ubigeo[r['ruc']] = r['ubigeo']
    rows = []
    for p in sorted(folder.glob('*.html')):
        if not re.fullmatch(r'\d{11}', p.stem):
            continue
        try:
            f = pf.parse_ficha(p.read_text(encoding='utf-8', errors='replace'), expected_ruc=p.stem)
        except pf.ParseError:
            continue
        facts = sc.facts_from_ficha(f, pf.antiguedad_anios(f), ubigeo.get(f['ruc']))
        rows.append((f, sc.score(facts, sc.PROFILE_V1), sc.score(facts, sc.PROFILE_V2_PADRONES)))

    def show(f):
        natural = f['forma_societaria'] == 'NATURAL'
        return (f['ruc'][:2] + '·········' if natural else f['ruc']), ('(persona natural)' if natural else f['razon_social'][:36])

    def cell(r):
        return f"gate:{r['gate']}" if r['gate'] else f"{r['score']:>3} {r['tier']}"

    print(f"{'RUC':13} {'Empresa':37} {'Forma':8} {'v1 actual':>14} {'v2 con padrones':>16}")
    for f, a, b in sorted(rows, key=lambda x: (x[1]['score'] is None, -(x[1]['score'] or 0))):
        ruc, name = show(f)
        print(f"{ruc:13} {name:37} {f['forma_societaria']:8} {cell(a):>14} {cell(b):>16}")
    for label, idx in (('v1 (actual)', 1), ('v2 (P1, con padrones)', 2)):
        res = [r[idx] for r in rows]
        print(f"\n{label}: niveles {dict(sorted(Counter(r['tier'] for r in res if r['tier']).items()))} · descartadas por filtro {dict(Counter(r['gate'] for r in res if r['gate']))}")
    cambian = [(show(f)[0], a['tier'], b['tier']) for f, a, b in rows if a['tier'] != b['tier']]
    print(f"\nCambian de nivel con P1: {len(cambian)} de {len(rows)}")
    for ruc, ta, tb in cambian:
        print(f"   {ruc}: {ta} → {tb}")
    if csv_out:
        out = pathlib.Path(csv_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['ruc', 'razon_social', 'forma', 'gate_v1', 'score_v1', 'tier_v1', 'tope_v1', 'score_v2', 'tier_v2', 'padrones_vigentes'])
            for f, a, b in rows:
                natural = f['forma_societaria'] == 'NATURAL'
                w.writerow([f['ruc'], '' if natural else f['razon_social'], f['forma_societaria'], a['gate'] or '', a['score'] if a['score'] is not None else '',
                            a['tier'] or '', a['tier_cap']['rule'] if a['tier_cap'] else '', b['score'] if b['score'] is not None else '', b['tier'] or '',
                            '; '.join(sc.padrones_vigentes(f['padrones']))])
        print(f"\nEscribí {len(rows)} filas en {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
