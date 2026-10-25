"""Pruebas del motor de puntaje (scoring.py). Incluyen los casos AC-08 y AC-12 de docs/02 §5.

Uso: python3 -I scripts/spike/test_scoring.py
"""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scoring as sc  # noqa: E402


def facts(**over):
    base = {
        'estado': 'ACTIVO', 'condicion': 'HABIDO', 'comercio_exterior': ['IMPORTADOR'],
        'actividades': [{'kind': 'PRINCIPAL', 'position': 0, 'ciiu_code': '4652', 'description': 'x'}],
        'antiguedad_anios': 7.0, 'forma_societaria': 'SAC', 'emite_factura': True, 'emisor_electronico': True,
        'ubigeo': '150101', 'padrones': [], 'excluido': False,
    }
    base.update(over)
    return base


def by_key(res):
    return {i['key']: i['points'] for i in res['items']}


class ProfileTests(unittest.TestCase):
    def test_example_profiles_are_valid(self):
        self.assertEqual(sc.validate_profile(sc.PROFILE_V1), [])
        self.assertEqual(sc.validate_profile(sc.PROFILE_V2_PADRONES), [])

    def test_validation_catches_bad_profiles(self):
        bad = copy.deepcopy(sc.PROFILE_V1)
        bad['criteria']['rubro']['max'] = 50
        self.assertTrue(any('suman' in p for p in sc.validate_profile(bad)))
        bad = copy.deepcopy(sc.PROFILE_V1)
        bad['tiers'] = {'A': 50, 'B': 55, 'C': 35}
        self.assertTrue(any('umbrales' in p for p in sc.validate_profile(bad)))
        bad = copy.deepcopy(sc.PROFILE_V1)
        bad['ciiu_weights']['4652'] = 1.5
        self.assertTrue(any('peso' in p for p in sc.validate_profile(bad)))


class ScoreTests(unittest.TestCase):
    def test_ac08_perfect_company_scores_100_tier_a(self):
        r = sc.score(facts(), sc.PROFILE_V1)
        self.assertEqual((r['score'], r['tier'], r['gate']), (100, 'A', None))
        self.assertEqual(by_key(r), {'rubro': 45, 'antiguedad': 25, 'forma_societaria': 10, 'comprobantes': 10, 'logistica': 10})
        self.assertTrue(all(i['note'] for i in r['items']))  # cada línea se puede explicar

    def test_ac12_young_company_is_capped_at_b_but_keeps_its_score(self):
        r = sc.score(facts(antiguedad_anios=3.0), sc.PROFILE_V1)
        self.assertEqual(r['score'], 93)
        self.assertEqual(r['tier'], 'B')
        self.assertEqual(r['tier_cap'], {'rule': 'antiguedad_years_lt_5', 'from': 'A', 'to': 'B'})

    def test_cap_does_not_raise_a_low_tier(self):
        r = sc.score(facts(antiguedad_anios=1.0, actividades=[], forma_societaria='EIRL', ubigeo=None, emite_factura=False, emisor_electronico=False), sc.PROFILE_V1)
        self.assertEqual(r['tier'], 'D')
        self.assertIsNone(r['tier_cap'])

    def test_gates(self):
        casos = {'estado': facts(estado='BAJA DE OFICIO'), 'condicion': facts(condicion='NO HABIDO'),
                 'comercio_exterior': facts(comercio_exterior=['SIN ACTIVIDAD']),
                 'comercio_exterior ': facts(comercio_exterior=['EXPORTADOR']),
                 'excluido_manualmente': facts(excluido=True)}
        for esperado, f in casos.items():
            r = sc.score(f, sc.PROFILE_V1)
            self.assertEqual(r['gate'], esperado.strip(), esperado)
            self.assertIsNone(r['score'])
            self.assertIsNone(r['tier'])

    def test_importer_and_exporter_passes(self):
        self.assertIsNone(sc.score(facts(comercio_exterior=['IMPORTADOR', 'EXPORTADOR']), sc.PROFILE_V1)['gate'])

    def test_rubro_secondary_factor_and_rounding_half_up(self):
        sec = [{'kind': 'PRINCIPAL', 'position': 0, 'ciiu_code': '4690', 'description': ''},
               {'kind': 'SECUNDARIA', 'position': 1, 'ciiu_code': '4741', 'description': ''}]
        self.assertEqual(by_key(sc.score(facts(actividades=sec), sc.PROFILE_V1))['rubro'], 22)  # 45 × 0.6 × 0.8 = 21.6
        self.assertEqual(sc.round_half_up(2.5), 3)
        self.assertEqual(sc.round_half_up(0.5), 1)

    def test_rubro_takes_the_best_code_and_unknown_codes_weigh_zero(self):
        acts = [{'kind': 'PRINCIPAL', 'position': 0, 'ciiu_code': '4690', 'description': ''},
                {'kind': 'SECUNDARIA', 'position': 1, 'ciiu_code': '4652', 'description': ''}]
        self.assertEqual(by_key(sc.score(facts(actividades=acts), sc.PROFILE_V1))['rubro'], 36)  # 45 × 1.0 × 0.8
        self.assertEqual(by_key(sc.score(facts(actividades=[{'kind': 'PRINCIPAL', 'position': 0, 'ciiu_code': '93098', 'description': ''}]), sc.PROFILE_V1))['rubro'], 0)
        self.assertEqual(by_key(sc.score(facts(actividades=[]), sc.PROFILE_V1))['rubro'], 0)

    def test_antiguedad_steps_at_the_boundaries(self):
        esperado = {0.0: 0, 0.99: 0, 1.0: 10, 2.99: 10, 3.0: 18, 4.99: 18, 5.0: 25, 40.0: 25}
        for years, pts in esperado.items():
            self.assertEqual(by_key(sc.score(facts(antiguedad_anios=years), sc.PROFILE_V1))['antiguedad'], pts, years)
        self.assertEqual(by_key(sc.score(facts(antiguedad_anios=None), sc.PROFILE_V1))['antiguedad'], 0)

    def test_forma_societaria_values(self):
        esperado = {'SAC': 10, 'SA': 10, 'SRL': 10, 'EIRL': 6, 'NATURAL': 3, 'SUCURSAL': 0, 'OTRA': 0, None: 0}
        for forma, pts in esperado.items():
            self.assertEqual(by_key(sc.score(facts(forma_societaria=forma), sc.PROFILE_V1))['forma_societaria'], pts, forma)

    def test_comprobantes(self):
        self.assertEqual(by_key(sc.score(facts(emite_factura=True, emisor_electronico=False), sc.PROFILE_V1))['comprobantes'], 5)
        self.assertEqual(by_key(sc.score(facts(emite_factura=False, emisor_electronico=False), sc.PROFILE_V1))['comprobantes'], 0)

    def test_logistica(self):
        for ub, pts in {'150101': 10, '070101': 10, '040101': 0, None: 0, '': 0, '15': 0}.items():
            self.assertEqual(by_key(sc.score(facts(ubigeo=ub), sc.PROFILE_V1))['logistica'], pts, ub)

    def test_tier_thresholds(self):
        p = copy.deepcopy(sc.PROFILE_V1)
        p['tier_caps'] = []
        for total, tier in {100: 'A', 75: 'A', 74: 'B', 55: 'B', 54: 'C', 35: 'C', 34: 'D', 0: 'D'}.items():
            # fabricamos un perfil de un solo criterio cuyo puntaje es `total`
            q = {'version': 9, 'gates': p['gates'], 'tiers': p['tiers'], 'tier_caps': [],
                 'criteria': {'antiguedad': {'max': 100, 'steps': [{'min_years': 0, 'points': total}]}}}
            self.assertEqual(sc.score(facts(), q)['tier'], tier, total)

    def test_same_input_same_output(self):
        a = sc.score(facts(), sc.PROFILE_V1)
        b = sc.score(copy.deepcopy(facts()), copy.deepcopy(sc.PROFILE_V1))
        self.assertEqual(a, b)

    def test_score_does_not_modify_its_inputs(self):
        f, p = facts(), copy.deepcopy(sc.PROFILE_V1)
        f0, p0 = copy.deepcopy(f), copy.deepcopy(p)
        sc.score(f, p)
        self.assertEqual((f, p), (f0, p0))


class RubroCapTests(unittest.TestCase):
    """P4 / D-22: sin ningún punto de rubro, el nivel máximo es C (AC-13 de docs/02)."""
    NO_RUBRO = [{'kind': 'PRINCIPAL', 'position': 0, 'ciiu_code': '4690', 'description': ''}]

    def test_ac13_company_without_rubro_is_capped_at_c_but_keeps_its_score(self):
        r = sc.score(facts(actividades=self.NO_RUBRO), sc.PROFILE_V1)
        self.assertEqual(by_key(r)['rubro'], 0)
        self.assertEqual(r['score'], 55)  # 25 + 10 + 10 + 10: justo el umbral de B
        self.assertEqual(r['tier'], 'C')
        self.assertEqual(r['tier_cap'], {'rule': 'rubro_points_lt_1', 'from': 'B', 'to': 'C'})

    def test_without_the_cap_the_same_company_would_be_b(self):  # lo que corrige P4
        p = copy.deepcopy(sc.PROFILE_V1)
        p['tier_caps'] = [c for c in p['tier_caps'] if 'rubro_points_lt' not in c['when']]
        self.assertEqual(sc.score(facts(actividades=self.NO_RUBRO), p)['tier'], 'B')

    def test_any_rubro_point_avoids_the_cap(self):
        acts = [{'kind': 'PRINCIPAL', 'position': 0, 'ciiu_code': '4659', 'description': ''}]  # peso 0.2 → 9 puntos
        r = sc.score(facts(actividades=acts), sc.PROFILE_V1)
        self.assertEqual(by_key(r)['rubro'], 9)
        self.assertEqual((r['score'], r['tier']), (64, 'B'))
        self.assertIsNone(r['tier_cap'])

    def test_company_without_activities_is_also_capped(self):
        r = sc.score(facts(actividades=[]), sc.PROFILE_V1)
        self.assertEqual((r['score'], r['tier']), (55, 'C'))

    def test_both_caps_are_listed_even_when_the_tier_was_already_low(self):
        r = sc.score(facts(actividades=self.NO_RUBRO, antiguedad_anios=3.0), sc.PROFILE_V1)
        self.assertEqual(r['score'], 48)
        self.assertEqual(r['tier'], 'C')
        self.assertEqual(r['caps_triggered'], ['antiguedad_years_lt_5', 'rubro_points_lt_1'])
        self.assertIsNone(r['tier_cap'])  # ya era C: ningún tope bajó el nivel

    def test_chained_caps_report_the_rule_that_set_the_final_tier(self):
        p = copy.deepcopy(sc.PROFILE_V1)
        p['tiers'] = {'A': 40, 'B': 30, 'C': 10}  # 48 puntos serían A sin topes
        r = sc.score(facts(actividades=self.NO_RUBRO, antiguedad_anios=3.0), p)
        self.assertEqual(r['tier'], 'C')
        self.assertEqual(r['tier_cap'], {'rule': 'rubro_points_lt_1', 'from': 'A', 'to': 'C'})
        self.assertEqual(r['caps_triggered'], ['antiguedad_years_lt_5', 'rubro_points_lt_1'])

    def test_ac12_young_company_with_rubro_does_not_trigger_the_rubro_cap(self):
        r = sc.score(facts(antiguedad_anios=3.0), sc.PROFILE_V1)
        self.assertEqual(r['caps_triggered'], ['antiguedad_years_lt_5'])

    def test_a_profile_without_a_rubro_criterion_ignores_the_rubro_cap(self):
        q = copy.deepcopy(sc.PROFILE_V1)
        del q['criteria']['rubro']
        r = sc.score(facts(actividades=self.NO_RUBRO), q)
        self.assertEqual((r['score'], r['tier'], r['caps_triggered']), (55, 'B', []))

    def test_profile_v2_has_the_same_cap(self):
        r = sc.score(facts(actividades=self.NO_RUBRO, padrones=[PadronesTests.BC, PadronesTests.AR_IN]), sc.PROFILE_V2_PADRONES)
        self.assertEqual((r['score'], r['tier']), (55, 'C'))  # 25 + 10 + 10 (padrones) + 10 de logística

    def test_profile_validation_checks_the_caps(self):
        bad = copy.deepcopy(sc.PROFILE_V1)
        bad['tier_caps'].append({'when': {'color': 1}, 'max_tier': 'C'})
        self.assertTrue(any('condición desconocida' in p for p in sc.validate_profile(bad)))
        bad = copy.deepcopy(sc.PROFILE_V1)
        bad['tier_caps'][1]['max_tier'] = 'Z'
        self.assertTrue(any('nivel máximo inválido' in p for p in sc.validate_profile(bad)))


class PadronesTests(unittest.TestCase):
    BC = 'Incorporado al Régimen de Buenos Contribuyentes (Resolución N° 0210050002204) a partir del 01/02/2015'
    AR_IN = 'Incorporado al Régimen de Agentes de Retención de IGV (R.S.378-2013) a partir del 01/03/2014'
    AR_OUT = 'Excluido del Régimen de Agentes de Retención de IGV a partir del 01/02/2026'
    PE_OUT = 'Excluido del Régimen de Agentes de Percepción de IGV - Venta Interna a partir del 01/02/2016'

    def test_vigentes(self):
        self.assertEqual(sc.padrones_vigentes([self.BC, self.AR_IN]), ['Agentes de Retención de IGV', 'Buenos Contribuyentes'])

    def test_later_exclusion_cancels_the_incorporation(self):
        self.assertEqual(sc.padrones_vigentes([self.AR_IN, self.AR_OUT]), [])
        self.assertEqual(sc.padrones_vigentes([self.AR_OUT, self.AR_IN]), [])  # el orden de las líneas no importa

    def test_reincorporation_after_exclusion_counts(self):
        again = 'Incorporado al Régimen de Agentes de Retención de IGV (R.S.367-2025) a partir del 01/03/2026'
        self.assertEqual(sc.padrones_vigentes([self.AR_IN, self.AR_OUT, again]), ['Agentes de Retención de IGV'])

    def test_exclusion_alone_and_garbage_lines_are_ignored(self):
        self.assertEqual(sc.padrones_vigentes([self.PE_OUT, 'cualquier cosa', '']), [])

    def test_same_day_exclusion_wins(self):
        a = 'Incorporado al Régimen de Buenos Contribuyentes (R. 1) a partir del 01/02/2020'
        b = 'Excluido del Régimen de Buenos Contribuyentes a partir del 01/02/2020'
        self.assertEqual(sc.padrones_vigentes([a, b]), [])

    def test_profile_v2_uses_padrones_instead_of_comprobantes(self):
        r = sc.score(facts(padrones=[self.BC, self.AR_IN]), sc.PROFILE_V2_PADRONES)
        self.assertEqual(by_key(r), {'rubro': 45, 'antiguedad': 25, 'forma_societaria': 10, 'padrones': 10, 'logistica': 10})
        self.assertEqual(r['score'], 100)
        solo_bc = sc.score(facts(padrones=[self.BC]), sc.PROFILE_V2_PADRONES)
        self.assertEqual(by_key(solo_bc)['padrones'], 6)
        sin = sc.score(facts(padrones=[self.AR_IN, self.AR_OUT]), sc.PROFILE_V2_PADRONES)
        self.assertEqual(by_key(sin)['padrones'], 0)
        self.assertEqual(sin['score'], 90)


if __name__ == '__main__':
    unittest.main(verbosity=2)
