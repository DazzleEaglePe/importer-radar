"""Consulta RUC automática (versión del spike): abre TU Chrome, consulta cada RUC y guarda la ficha.

LO EJECUTAS TÚ, en tu Mac. El robots.txt de e-consultaruc.sunat.gob.pe bloquea a los agentes de Anthropic,
así que este programa lo escribe Claude pero no lo ejecuta contra esa página (docs/01 §9.1, D-18, D-21).

Reglas de cortesía (docs/03 RNF-COR):
    - una consulta a la vez, con espera aleatoria entre consultas (por defecto 6 a 12 s);
    - tope diario (por defecto 400) y tope por ejecución (por defecto 20);
    - si SUNAT pide una verificación humana, NO se intenta resolver ni esquivar: el programa te avisa y
      espera a que TÚ la resuelvas en la ventana; si hay un bloqueo (403, 429, «demasiadas consultas»), se detiene;
    - es reanudable: salta los RUC que ya tienen su archivo `<ruc>.html`.

Ejemplos:
    # primera vez, con la muestra de 20 (Chrome visible y capturas para revisar el diseño)
    .venv/bin/python -I scripts/spike/lookup_fetch.py \\
        --list data/processed/aduanet/2026-10-25/sp06_muestra_20_ruc.csv \\
        --out data/raw/consulta_ruc/2026-10-25 --max 20 --screenshot --ruc 20526185847

    # un día de trabajo (los 400 de mayor prioridad que falten)
    .venv/bin/python -I scripts/spike/lookup_fetch.py \\
        --list data/processed/aduanet/2026-10-25/importadores_activo_habido.csv \\
        --out data/raw/consulta_ruc/2026-10-25 --max 400

Solo biblioteca estándar, salvo Playwright (se importa al abrir el navegador). Compatible con Python 3.9.
"""
import argparse
import csv
import datetime
import json
import pathlib
import random
import re
import sys
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

FORM_URL = 'https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp'

OK, NOT_FOUND, NEEDS_HUMAN, BLOCKED, ERROR = 'OK', 'NOT_FOUND', 'NEEDS_HUMAN', 'BLOCKED', 'ERROR'

RESULT_RE = re.compile(r'N[uú]mero de RUC', re.I)
NOTFOUND_RE = re.compile(r'no existe|no se encontr|sin resultados|no hay resultados', re.I)
CHALLENGE_RE = re.compile(
    r'captcha|verifica(?:r)? que (?:eres|no eres)|verify you are human|just a moment|checking your browser|'
    r'turnstile|desaf[ií]o de seguridad', re.I)
BLOCK_RE = re.compile(
    r'access denied|acceso denegado|demasiadas (?:consultas|solicitudes|peticiones)|too many requests|'
    r'rate limit|has sido bloquead|you have been blocked', re.I)


@dataclass
class Result:
    outcome: str
    html: Optional[str] = None
    note: str = ''
    shot: Optional[bytes] = None


def ruc_ok(r: str) -> bool:
    """Formato de 11 dígitos y dígito verificador (módulo 11)."""
    if len(r) != 11 or not r.isdigit():
        return False
    w = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    d = 11 - (sum(int(r[i]) * w[i] for i in range(10)) % 11)
    d = {10: 0, 11: 1}.get(d, d)
    return d == int(r[10])


def classify_text(text: str) -> Optional[str]:
    """Devuelve BLOCKED o NEEDS_HUMAN si el texto de la página lo indica; si no, None."""
    if BLOCK_RE.search(text):
        return BLOCKED
    if CHALLENGE_RE.search(text):
        return NEEDS_HUMAN
    return None


def load_rucs(list_path: Optional[str], extra: List[str]) -> Tuple[List[str], int]:
    """RUC en el orden del archivo (precedidos por --ruc), sin repetidos y válidos. Devuelve (lista, descartados)."""
    seen, out, bad = set(), [], 0
    candidates = list(extra)
    if list_path:
        with open(list_path, encoding='utf-8-sig', newline='') as f:
            candidates += [(row.get('ruc') or '').strip() for row in csv.DictReader(f)]
    for r in candidates:
        if r in seen:
            continue
        if not ruc_ok(r):
            bad += 1
            continue
        seen.add(r)
        out.append(r)
    return out, bad


def already_done(out_dir: pathlib.Path) -> set:
    return {p.stem for p in out_dir.glob('*.html') if re.fullmatch(r'\d{11}', p.stem)}


def done_today(log_path: pathlib.Path, today: str) -> int:
    n = 0
    if log_path.exists():
        for line in log_path.read_text(encoding='utf-8').splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get('ts', '').startswith(today) and rec.get('outcome') in (OK, NOT_FOUND):
                n += 1
    return n


def run(rucs: List[str], fetch_one: Callable[[str], Result], out_dir: pathlib.Path, *, max_n: int,
        daily_cap: int, delay: Tuple[float, float], sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime.datetime] = datetime.datetime.now,
        ask_human: Optional[Callable[[int], bool]] = None, rng: Optional[random.Random] = None,
        max_errors_in_row: int = 3, say: Callable[[str], None] = print) -> Dict:
    """Recorre los RUC pendientes respetando ritmo y topes. Es independiente del navegador (se prueba con un doble)."""
    rng = rng or random.Random()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / 'lookups.jsonl'
    done = already_done(out_dir)
    pending = [r for r in rucs if r not in done]
    today = now().date().isoformat()
    today_count = done_today(log_path, today)
    summary = {'pendientes_al_inicio': len(pending), 'ya_hechos': len(rucs) - len(pending), 'intentos': 0,
               OK: 0, NOT_FOUND: 0, NEEDS_HUMAN: 0, BLOCKED: 0, ERROR: 0, 'parada': 'se acabaron los pendientes'}
    errors_in_row = 0
    handled = 0
    for idx, ruc in enumerate(pending, 1):
        if handled >= max_n:
            summary['parada'] = f'tope por ejecución ({max_n})'
            break
        if today_count >= daily_cap:
            summary['parada'] = f'tope diario ({daily_cap}) alcanzado'
            break
        if summary['intentos'] > 0:
            sleep(rng.uniform(*delay))
        t0 = time.time()
        res = fetch_one(ruc)
        logged = False
        if res.outcome == NEEDS_HUMAN:
            summary[NEEDS_HUMAN] += 1  # una verificación pedida (dato para SP-07), aunque se reintente
            _log(log_path, now, ruc, res, time.time() - t0)
            logged = True
            if ask_human is not None and ask_human(idx):
                t0 = time.time()
                res = fetch_one(ruc)
                logged = False
        summary['intentos'] += 1
        handled += 1
        if res.outcome != NEEDS_HUMAN:
            summary[res.outcome] += 1
        if not logged:
            _log(log_path, now, ruc, res, time.time() - t0)
        if res.outcome in (OK, NOT_FOUND):
            (out_dir / f'{ruc}.html').write_text(res.html or '', encoding='utf-8')
            today_count += 1
            errors_in_row = 0
            if res.shot:
                (out_dir / f'{ruc}.png').write_bytes(res.shot)
            say(f'[{handled}] {res.outcome}  ({len(res.html or "")/1024:.0f} KB)')
            continue
        if res.html:
            (out_dir / f'{ruc}.{res.outcome.lower()}.html').write_text(res.html, encoding='utf-8')
        if res.outcome == BLOCKED:
            summary['parada'] = f'bloqueo de la fuente: {res.note}'
            break
        if res.outcome == NEEDS_HUMAN:
            summary['parada'] = 'SUNAT pidió verificación humana y no se resolvió'
            break
        errors_in_row += 1
        say(f'[{handled}] ERROR: {res.note}')
        if errors_in_row >= max_errors_in_row:
            summary['parada'] = f'{max_errors_in_row} errores seguidos: {res.note}'
            break
    return summary


def _log(log_path: pathlib.Path, now: Callable[[], datetime.datetime], ruc: str, res: Result, secs: float) -> None:
    rec = {'ts': now().isoformat(timespec='seconds'), 'ruc': ruc, 'outcome': res.outcome,
           'bytes': len(res.html or ''), 'seconds': round(secs, 1), 'note': res.note}
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def ask_human_tty(idx: int) -> bool:
    if not sys.stdin.isatty():
        return False
    print(f'\n⚠  SUNAT pidió una verificación (consulta n.º {idx}).')
    print('   Resuélvela TÚ en la ventana del navegador. El programa no intenta resolverla ni esquivarla.')
    ans = input('   Pulsa Enter cuando termines para reintentar, o escribe «s» para salir: ')
    return ans.strip().lower() not in ('s', 'salir')


class PlaywrightDriver:
    """Controla tu Chrome (instalado en el Mac) con una ventana y un perfil temporal. Sin cambiar la identidad del navegador."""

    def __init__(self, headless: bool = False, channel: str = 'chrome', timeout_s: int = 30, shots: bool = False,
                 form_url: Optional[str] = None):
        self.headless, self.channel, self.timeout_s, self.shots = headless, channel, timeout_s, shots
        self.form_url = form_url  # solo para pruebas locales; si es None se usa FORM_URL

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(channel=self.channel, headless=self.headless)
        self._ctx = self._browser.new_context(locale='es-PE', viewport={'width': 1280, 'height': 1000})
        self.page = self._ctx.new_page()
        self.page.set_default_timeout(self.timeout_s * 1000)
        return self

    def __exit__(self, *exc):
        try:
            self._browser.close()
        finally:
            self._pw.stop()

    def _frames(self):
        return [self.page.main_frame] + [f for f in self.page.frames if f != self.page.main_frame]

    def _text(self, frame) -> str:
        try:
            return frame.inner_text('body', timeout=2000)
        except Exception:
            return ''

    def _all_text(self) -> str:
        return '\n'.join(self._text(f) for f in self._frames())

    def _find(self, getter):
        for f in self._frames():
            try:
                loc = getter(f)
                if loc.count() > 0:
                    return loc.first
            except Exception:
                continue
        return None

    def fetch(self, ruc: str) -> Result:
        page = self.page
        try:
            resp = page.goto(self.form_url or FORM_URL, wait_until='domcontentloaded')
        except Exception as e:
            return Result(ERROR, note=f'no pude abrir el formulario: {str(e)[:120]}')
        if resp is not None and resp.status in (403, 429):
            return Result(BLOCKED, note=f'HTTP {resp.status} al abrir el formulario')
        box = self._find(lambda f: f.get_by_placeholder('Ingrese RUC'))
        if box is None:
            kind = classify_text(self._all_text())
            return Result(kind or ERROR, html=page.content(), note='no apareció el campo «Ingrese RUC»')
        box.fill(ruc)
        button = self._find(lambda f: f.get_by_role('button', name='Buscar'))
        if button is None:
            return Result(ERROR, html=page.content(), note='no encontré el botón «Buscar»')
        button.click()
        deadline = time.time() + self.timeout_s
        while time.time() < deadline:
            for f in self._frames():
                if RESULT_RE.search(self._text(f)):
                    try:
                        page.wait_for_load_state('networkidle', timeout=8000)
                    except Exception:
                        pass
                    shot = page.screenshot(full_page=True) if self.shots else None
                    return Result(OK, html=f.content(), shot=shot)
            if classify_text(self._all_text()):
                break
            time.sleep(0.5)
        text = self._all_text()
        kind = classify_text(text)
        if kind:
            return Result(kind, html=page.content(), note='tras pulsar «Buscar»')
        if NOTFOUND_RE.search(text):
            return Result(NOT_FOUND, html=page.content(), note='SUNAT no devolvió ficha')
        return Result(ERROR, html=page.content(), note='la ficha no apareció a tiempo')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Consulta RUC automática con tu Chrome (lo ejecutas tú).')
    ap.add_argument('--list', help='CSV con una columna «ruc» (en el orden en que se consultarán)')
    ap.add_argument('--ruc', action='append', default=[], help='RUC extra al inicio (se puede repetir)')
    ap.add_argument('--out', required=True, help='carpeta donde se guardan las fichas')
    ap.add_argument('--max', type=int, default=20, help='máximo de consultas en esta ejecución (por defecto 20)')
    ap.add_argument('--daily-cap', type=int, default=400, help='tope diario (por defecto 400)')
    ap.add_argument('--delay', default='6,12', help='espera aleatoria entre consultas en segundos «mín,máx»')
    ap.add_argument('--headless', action='store_true', help='sin ventana (si hay verificación, se detiene)')
    ap.add_argument('--screenshot', action='store_true', help='guarda también una captura de cada ficha')
    ap.add_argument('--dry-run', action='store_true', help='solo muestra el plan, sin abrir el navegador')
    ap.add_argument('--form-url', default=None, help='solo para pruebas: una página LOCAL que imita el formulario')
    args = ap.parse_args(argv)
    if args.form_url and not re.match(r'^http://(127\.0\.0\.1|localhost)(:\d+)?/', args.form_url):
        print('--form-url solo acepta direcciones locales (http://127.0.0.1 o http://localhost).')
        return 2

    lo, hi = (float(x) for x in args.delay.split(','))
    if lo < 3 or hi < lo:
        print('La espera mínima debe ser de al menos 3 s y el máximo no puede ser menor que el mínimo.')
        return 2
    if args.max > 1000 or args.daily_cap > 1000:
        print('Por cortesía con SUNAT, los topes no pueden pasar de 1000.')
        return 2
    rucs, bad = load_rucs(args.list, args.ruc)
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = already_done(out_dir)
    pend = [r for r in rucs if r not in done]
    print(f'RUC válidos: {len(rucs):,} (descartados por formato o dígito verificador: {bad}) · '
          f'ya consultados: {len(rucs) - len(pend):,} · pendientes: {len(pend):,}')
    today_n = done_today(out_dir / 'lookups.jsonl', datetime.date.today().isoformat())
    print(f'Consultas de hoy: {today_n} de {args.daily_cap} · en esta ejecución: hasta {args.max}')
    if args.dry_run:
        print('Modo de prueba (--dry-run): no se abre el navegador.')
        return 0
    if not pend:
        print('No hay nada pendiente.')
        return 0
    print('Abriendo Chrome. Puedes ver todo lo que hace. Ctrl+C para parar cuando quieras.\n')
    try:
        with PlaywrightDriver(headless=args.headless, shots=args.screenshot, form_url=args.form_url) as drv:
            summary = run(rucs, drv.fetch, out_dir, max_n=args.max, daily_cap=args.daily_cap, delay=(lo, hi),
                          ask_human=None if args.headless else ask_human_tty)
    except KeyboardInterrupt:
        print('\nInterrumpido por ti. Lo ya guardado se conserva y puedes reanudar.')
        return 130
    print('\n== Resumen ==')
    for k, v in summary.items():
        print(f'  {k}: {v}')
    print(f'\nVerificaciones pedidas por SUNAT en esta ejecución: {summary[NEEDS_HUMAN]}  (dato para SP-07)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
