"""Pruebas de la lógica de lookup_fetch.py con un navegador simulado (no toca SUNAT ni abre Chrome).

Uso: python3 -I scripts/spike/test_lookup_fetch.py
"""
import contextlib
import datetime
import io
import json
import pathlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lookup_fetch as lf  # noqa: E402


def mk(n: int) -> str:
    """RUC válido de prueba (prefijo 20) a partir de un número."""
    base = '20' + str(n).zfill(8)
    w = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    d = 11 - (sum(int(base[i]) * w[i] for i in range(10)) % 11)
    return base + str({10: 0, 11: 1}.get(d, d))


class Fake:
    """Doble del navegador: devuelve resultados guiados por RUC; por defecto, una ficha OK."""

    def __init__(self, script=None):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.calls = []

    def __call__(self, ruc):
        self.calls.append(ruc)
        queue = self.script.get(ruc)
        if queue:
            return queue.pop(0)
        return lf.Result(lf.OK, html=f'<html>ficha {ruc}</html>')


class RunTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self._tmp.name) / 'fichas'
        self.sleeps = []
        self.fixed_now = lambda: datetime.datetime(2026, 10, 25, 12, 0, 0)

    def tearDown(self):
        self._tmp.cleanup()

    def go(self, rucs, fake, **kw):
        params = dict(max_n=20, daily_cap=400, delay=(6, 12), sleep=self.sleeps.append, now=self.fixed_now,
                      rng=random.Random(1), say=lambda s: None)
        params.update(kw)
        return lf.run(rucs, fake, self.out, **params)

    def test_ruc_validation(self):
        self.assertTrue(lf.ruc_ok('20526185847'))
        self.assertFalse(lf.ruc_ok('20526185848'))
        self.assertFalse(lf.ruc_ok('2052618584'))
        self.assertFalse(lf.ruc_ok('AA526185847'))

    def test_classify_text(self):
        self.assertEqual(lf.classify_text('Demasiadas consultas, intente luego'), lf.BLOCKED)
        self.assertEqual(lf.classify_text('Por favor resuelva el CAPTCHA'), lf.NEEDS_HUMAN)
        self.assertEqual(lf.classify_text('Just a moment...'), lf.NEEDS_HUMAN)
        self.assertIsNone(lf.classify_text('Consulta RUC. Número de RUC: 20526185847'))

    def test_load_rucs_filters_and_dedupes(self):
        p = pathlib.Path(self._tmp.name) / 'l.csv'
        p.write_text('n,ruc\n1,%s\n2,%s\n3,20526185848\n4,%s\n' % (mk(1), mk(2), mk(1)), encoding='utf-8-sig')
        rucs, bad = lf.load_rucs(str(p), ['20526185847'])
        self.assertEqual(rucs, ['20526185847', mk(1), mk(2)])
        self.assertEqual(bad, 1)

    def test_basic_run_writes_files_and_log(self):
        rucs = [mk(i) for i in range(1, 4)]
        s = self.go(rucs, Fake())
        self.assertEqual(s[lf.OK], 3)
        self.assertEqual(s['parada'], 'se acabaron los pendientes')
        for r in rucs:
            self.assertTrue((self.out / f'{r}.html').exists())
        lines = (self.out / 'lookups.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[0])['outcome'], lf.OK)
        self.assertEqual(len(self.sleeps), 2)  # entre consultas, no antes de la primera
        self.assertTrue(all(6 <= x <= 12 for x in self.sleeps))

    def test_resume_skips_done(self):
        rucs = [mk(i) for i in range(1, 4)]
        self.out.mkdir(parents=True)
        (self.out / f'{rucs[0]}.html').write_text('ya', encoding='utf-8')
        fake = Fake()
        s = self.go(rucs, fake)
        self.assertEqual(fake.calls, rucs[1:])
        self.assertEqual(s['ya_hechos'], 1)

    def test_max_per_run(self):
        fake = Fake()
        s = self.go([mk(i) for i in range(1, 6)], fake, max_n=2)
        self.assertEqual(len(fake.calls), 2)
        self.assertIn('ejecución', s['parada'])

    def test_daily_cap_counts_previous_runs_today(self):
        self.out.mkdir(parents=True)
        with open(self.out / 'lookups.jsonl', 'w', encoding='utf-8') as f:
            for i in range(3):
                f.write(json.dumps({'ts': '2026-10-25T09:00:0%d' % i, 'ruc': mk(90 + i), 'outcome': lf.OK}) + '\n')
            f.write(json.dumps({'ts': '2026-10-24T09:00:00', 'ruc': mk(99), 'outcome': lf.OK}) + '\n')  # ayer no cuenta
        fake = Fake()
        s = self.go([mk(i) for i in range(1, 6)], fake, daily_cap=4)
        self.assertEqual(len(fake.calls), 1)
        self.assertIn('diario', s['parada'])

    def test_blocked_stops_immediately(self):
        rucs = [mk(i) for i in range(1, 5)]
        fake = Fake({rucs[1]: [lf.Result(lf.BLOCKED, html='<html>403</html>', note='HTTP 429')]})
        s = self.go(rucs, fake)
        self.assertEqual(fake.calls, rucs[:2])
        self.assertEqual(s[lf.BLOCKED], 1)
        self.assertIn('bloqueo', s['parada'])
        self.assertFalse((self.out / f'{rucs[1]}.html').exists())
        self.assertTrue((self.out / f'{rucs[1]}.blocked.html').exists())

    def test_needs_human_without_help_stops(self):
        rucs = [mk(i) for i in range(1, 4)]
        fake = Fake({rucs[0]: [lf.Result(lf.NEEDS_HUMAN, html='<html>captcha</html>')]})
        s = self.go(rucs, fake, ask_human=None)
        self.assertEqual(fake.calls, rucs[:1])
        self.assertEqual(s[lf.NEEDS_HUMAN], 1)
        self.assertIn('verificación', s['parada'])

    def test_needs_human_person_resolves_and_it_continues(self):
        rucs = [mk(i) for i in range(1, 4)]
        fake = Fake({rucs[0]: [lf.Result(lf.NEEDS_HUMAN, html='x'), lf.Result(lf.OK, html='<html>ok</html>')]})
        asked = []
        s = self.go(rucs, fake, ask_human=lambda i: asked.append(i) or True)
        self.assertEqual(asked, [1])
        self.assertEqual(s[lf.OK], 3)
        self.assertEqual(s[lf.NEEDS_HUMAN], 1)  # una verificación pedida
        self.assertEqual(fake.calls.count(rucs[0]), 2)

    def test_needs_human_person_declines_stops(self):
        rucs = [mk(i) for i in range(1, 4)]
        fake = Fake({rucs[0]: [lf.Result(lf.NEEDS_HUMAN, html='x')]})
        s = self.go(rucs, fake, ask_human=lambda i: False)
        self.assertEqual(fake.calls, rucs[:1])
        self.assertIn('verificación', s['parada'])

    def test_three_errors_in_a_row_stop_but_one_ok_resets(self):
        rucs = [mk(i) for i in range(1, 8)]
        err = lambda: lf.Result(lf.ERROR, html='<html>e</html>', note='raro')
        fake = Fake({rucs[0]: [err()], rucs[1]: [err()], rucs[3]: [err()], rucs[4]: [err()], rucs[5]: [err()]})
        s = self.go(rucs, fake)
        self.assertEqual(fake.calls, rucs[:6])  # el OK de rucs[2] reinició la cuenta; se detiene en el 3.º seguido
        self.assertIn('errores seguidos', s['parada'])
        self.assertTrue((self.out / f'{rucs[0]}.error.html').exists())
        self.assertFalse((self.out / f'{rucs[0]}.html').exists())  # un error no cuenta como hecho

    def test_not_found_counts_as_done(self):
        rucs = [mk(1)]
        fake = Fake({rucs[0]: [lf.Result(lf.NOT_FOUND, html='<html>no existe</html>')]})
        s = self.go(rucs, fake)
        self.assertEqual(s[lf.NOT_FOUND], 1)
        self.assertTrue((self.out / f'{rucs[0]}.html').exists())

    def test_screenshot_saved_when_present(self):
        fake = Fake({mk(1): [lf.Result(lf.OK, html='<html>ok</html>', shot=b'PNG')]})
        self.go([mk(1)], fake)
        self.assertEqual((self.out / f'{mk(1)}.png').read_bytes(), b'PNG')


class MainTests(unittest.TestCase):
    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lf.main(argv)
        return code, buf.getvalue()

    def test_rejects_aggressive_settings(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_main(['--out', d, '--delay', '1,2'])[0], 2)
            self.assertEqual(self.run_main(['--out', d, '--max', '5000'])[0], 2)
            self.assertEqual(self.run_main(['--out', d, '--daily-cap', '5000'])[0], 2)

    def test_dry_run_does_not_open_browser(self):
        with tempfile.TemporaryDirectory() as d:
            lst = pathlib.Path(d) / 'l.csv'
            lst.write_text('ruc\n%s\n%s\n' % (mk(1), mk(2)), encoding='utf-8')
            code, out = self.run_main(['--list', str(lst), '--out', str(pathlib.Path(d) / 'o'), '--dry-run'])
            self.assertEqual(code, 0)
            self.assertIn('pendientes: 2', out)
            self.assertIn('no se abre el navegador', out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
