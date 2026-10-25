"""Pruebas del NAVEGADOR de lookup_fetch.py contra una página local simulada. No toca SUNAT.

Levanta un servidor en 127.0.0.1 que imita el formulario («Ingrese RUC», «Buscar») y la ficha («Número de RUC»),
con casos de: ficha normal, formulario dentro de un iframe, respuesta lenta, RUC sin resultado,
verificación humana, bloqueo (429), ficha que nunca aparece y formulario roto.

Requiere Playwright y Chrome instalado:
    .venv/bin/python -I scripts/spike/test_lookup_browser.py
"""
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lookup_fetch as lf  # noqa: E402
from test_lookup_fetch import mk  # noqa: E402

try:
    import playwright.sync_api  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False

FORM_PATH = '/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp'
RESULT_PATH = '/cl-ti-itmrconsruc/jcrS00Alias'
MODE = {}        # ruc -> ok | slow | notfound | challenge | blocked | broken
SOLVED = set()   # RUC cuya «verificación» ya resolvió la persona
HITS = []        # (tipo, ruc) en el orden en que llegaron las consultas

FORM_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>SUNAT - Consulta Ruc</title></head>
<body><h1>Consulta RUC</h1>
<div><button type="button">Por RUC</button><button type="button">Por Documento</button><button type="button">Por Nomb./Raz.Soc.</button></div>
<input type="text" placeholder="Ingrese RUC" id="txtRuc">
<button type="button" onclick="location.href='%s?accion=consPorRuc&nroRuc='+document.getElementById('txtRuc').value">Buscar</button>
</body></html>""" % RESULT_PATH


def result_html(ruc):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>SUNAT - Consulta RUC</title></head><body>
<h2>Consulta RUC</h2><div><b>Resultado de la Búsqueda</b></div>
<table><tr><td>Número de RUC:</td><td>{ruc} - EMPRESA DE PRUEBA S.A.C.</td></tr>
<tr><td>Estado del Contribuyente:</td><td>ACTIVO</td></tr>
<tr><td>Condición del Contribuyente:</td><td>HABIDO</td></tr>
<tr><td>Actividad(es) Económica(s):</td><td>Principal - 4652 - VENTA AL POR MAYOR DE EQUIPO ELECTRÓNICO</td></tr></table>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, status=200):
        data = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == FORM_PATH:
            return self._send(FORM_HTML)
        if u.path == '/iframe':
            return self._send(f'<!doctype html><html><body><h1>Marco</h1><iframe src="{FORM_PATH}" width="900" height="500"></iframe></body></html>')
        if u.path == '/form_challenge':
            return self._send('<html><body><h3>Verificando que eres humano</h3><p>Completa el CAPTCHA para continuar</p></body></html>')
        if u.path == '/form_429':
            return self._send('<html><body><p>Too many requests</p></body></html>', 429)
        if u.path == '/form_maint':
            return self._send('<html><body><p>Servicio en mantenimiento</p></body></html>')
        if u.path == RESULT_PATH:
            ruc = parse_qs(u.query).get('nroRuc', [''])[0]
            mode = MODE.get(ruc, 'ok')
            HITS.append((mode, ruc))
            if mode == 'slow':
                time.sleep(1.5)
                return self._send(result_html(ruc))
            if mode == 'notfound':
                return self._send('<html><body><p>No existe el RUC ingresado</p></body></html>')
            if mode == 'challenge' and ruc not in SOLVED:
                return self._send('<html><body><h3>Verificando que eres humano</h3><p>Completa el CAPTCHA</p></body></html>')
            if mode == 'blocked':
                return self._send('<html><body><p>Too many requests. Demasiadas consultas.</p></body></html>', 429)
            if mode == 'broken':
                return self._send('<html><body><p>Cargando…</p></body></html>')
            return self._send(result_html(ruc))
        self._send('no encontrado', 404)


@unittest.skipUnless(HAVE_PW, 'Playwright no está instalado')
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.drv = lf.PlaywrightDriver(headless=True, timeout_s=4, shots=True)
        try:
            cls.drv.__enter__()
        except Exception as e:  # Chrome no instalado o no arranca
            cls.server.shutdown()
            raise unittest.SkipTest(f'No pude abrir Chrome con Playwright: {str(e)[:150]}')

    @classmethod
    def tearDownClass(cls):
        try:
            cls.drv.__exit__(None, None, None)
        finally:
            cls.server.shutdown()

    def setUp(self):
        MODE.clear()
        SOLVED.clear()
        HITS.clear()
        lf.FORM_URL = self.base + FORM_PATH

    def test_ok_normal_form(self):
        r = self.drv.fetch(mk(1))
        self.assertEqual(r.outcome, lf.OK, r.note)
        self.assertIn('Número de RUC', r.html)
        self.assertIn(mk(1), r.html)
        self.assertTrue(r.shot and r.shot[:4] == b'\x89PNG')

    def test_ok_form_inside_iframe(self):
        lf.FORM_URL = self.base + '/iframe'
        r = self.drv.fetch(mk(2))
        self.assertEqual(r.outcome, lf.OK, r.note)
        self.assertIn(mk(2), r.html)
        self.assertIn('ACTIVO', r.html)

    def test_slow_result_is_awaited(self):
        MODE[mk(3)] = 'slow'
        r = self.drv.fetch(mk(3))
        self.assertEqual(r.outcome, lf.OK, r.note)

    def test_not_found(self):
        MODE[mk(4)] = 'notfound'
        r = self.drv.fetch(mk(4))
        self.assertEqual(r.outcome, lf.NOT_FOUND, r.note)

    def test_challenge_is_reported_then_person_solves_it(self):
        MODE[mk(5)] = 'challenge'
        r = self.drv.fetch(mk(5))
        self.assertEqual(r.outcome, lf.NEEDS_HUMAN, r.note)
        SOLVED.add(mk(5))  # la persona resolvió la verificación
        r = self.drv.fetch(mk(5))
        self.assertEqual(r.outcome, lf.OK, r.note)

    def test_block_is_reported(self):
        MODE[mk(6)] = 'blocked'
        self.assertEqual(self.drv.fetch(mk(6)).outcome, lf.BLOCKED)

    def test_result_that_never_appears_is_an_error_not_a_hang(self):
        MODE[mk(7)] = 'broken'
        t0 = time.time()
        r = self.drv.fetch(mk(7))
        self.assertEqual(r.outcome, lf.ERROR)
        self.assertIn('a tiempo', r.note)
        self.assertLess(time.time() - t0, 15)
        self.assertIn('Cargando', r.html)  # se conserva lo que vio

    def test_form_without_input_is_an_error(self):
        lf.FORM_URL = self.base + '/form_maint'
        r = self.drv.fetch(mk(8))
        self.assertEqual(r.outcome, lf.ERROR)
        self.assertIn('Ingrese RUC', r.note)

    def test_challenge_on_the_form_page(self):
        lf.FORM_URL = self.base + '/form_challenge'
        self.assertEqual(self.drv.fetch(mk(9)).outcome, lf.NEEDS_HUMAN)

    def test_http_429_on_the_form_page(self):
        lf.FORM_URL = self.base + '/form_429'
        r = self.drv.fetch(mk(10))
        self.assertEqual(r.outcome, lf.BLOCKED)
        self.assertIn('429', r.note)

    def test_full_pipeline_with_the_real_driver(self):
        a, b, c, d, e = (mk(20 + i) for i in range(5))
        MODE[b] = 'challenge'
        MODE[d] = 'blocked'

        def person_solves(idx):
            SOLVED.add(b)
            return True

        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'fichas'
            s = lf.run([a, b, c, d, e], self.drv.fetch, out, max_n=20, daily_cap=400, delay=(0, 0),
                       sleep=lambda x: None, ask_human=person_solves, say=lambda x: None)
            self.assertEqual(s[lf.OK], 3)
            self.assertEqual(s[lf.NEEDS_HUMAN], 1)
            self.assertEqual(s[lf.BLOCKED], 1)
            self.assertIn('bloqueo', s['parada'])
            for r in (a, b, c):
                self.assertIn(f'{r}', (out / f'{r}.html').read_text(encoding='utf-8'))
            self.assertTrue((out / f'{d}.blocked.html').exists())
            self.assertFalse((out / f'{e}.html').exists())
            self.assertEqual([h for h in HITS], [('ok', a), ('challenge', b), ('challenge', b), ('ok', c), ('blocked', d)])
            # a (ok) · b (verificación) · b (reintento ok) · c (ok) · d (bloqueo)
            self.assertEqual(len((out / 'lookups.jsonl').read_text(encoding='utf-8').splitlines()), 5)

    def test_main_end_to_end_headless_in_a_subprocess(self):
        """El programa completo, tal como lo lanzarías tú, contra la página local (otro proceso: dos Playwright no caben en uno)."""
        with tempfile.TemporaryDirectory() as tmp:
            lst = pathlib.Path(tmp) / 'l.csv'
            lst.write_text('ruc\n%s\n%s\n' % (mk(31), mk(32)), encoding='utf-8')
            out = pathlib.Path(tmp) / 'o'
            p = subprocess.run([sys.executable, '-I', str(pathlib.Path(lf.__file__)), '--list', str(lst), '--out', str(out),
                                '--max', '2', '--delay', '3,3', '--headless', '--form-url', self.base + FORM_PATH],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertTrue((out / f'{mk(31)}.html').exists() and (out / f'{mk(32)}.html').exists())
            self.assertIn('Verificaciones pedidas', p.stdout)
            self.assertIn('ok', [h[0] for h in HITS])

    def test_form_url_only_accepts_local_addresses(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lf.main(['--out', tempfile.gettempdir(), '--form-url', 'https://otro-sitio.example/formulario'])
        self.assertEqual(code, 2)
        self.assertIn('solo acepta direcciones locales', buf.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
