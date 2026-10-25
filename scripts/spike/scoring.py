"""Motor de puntaje (prototipo del spike): función PURA, sin base de datos ni red (docs/05 §6, docs/01 §6).

    score(facts, profile) -> {'gate': None | 'estado' | ..., 'score': int | None, 'tier': 'A'..'D' | None,
                              'items': [...], 'tier_cap': None | {...}}

- Primero los filtros eliminatorios («gates»): si fallan, no hay puntaje ni nivel.
- Luego los criterios, cada uno con su máximo. La suma de los máximos de un perfil es 100.
- Por último los niveles, con los topes (`tier_caps`) que limitan el nivel sin tocar el puntaje.
- Redondeo «mitad hacia arriba» (no el redondeo bancario de Python), para que el resultado sea igual en cualquier lenguaje.

Dos perfiles de ejemplo: `PROFILE_V1` (el de docs/05 tras D-20) y `PROFILE_V2_PADRONES` (la propuesta P1 de docs/12 §7.3).
Compatible con Python 3.9, solo biblioteca estándar.
"""
import copy
import re
from typing import Dict, List, Optional

CIIU_WEIGHTS_SMARTPHONES = {'4652': 1.0, '4651': 1.0, '4741': 0.6, '4742': 0.3, '4659': 0.2}

PROFILE_V1 = {
    'key': 'smartphones', 'name': 'Smartphones / iPhone', 'version': 1,
    'gates': {'estado': ['ACTIVO'], 'condicion': ['HABIDO'], 'comercio_exterior_requiere': ['IMPORTADOR']},
    'criteria': {
        'rubro': {'max': 45, 'secondary_factor': 0.8},
        'antiguedad': {'max': 25, 'steps': [{'min_years': 0, 'points': 0}, {'min_years': 1, 'points': 10},
                                            {'min_years': 3, 'points': 18}, {'min_years': 5, 'points': 25}]},
        'forma_societaria': {'max': 10, 'values': {'SA': 10, 'SAC': 10, 'SRL': 10, 'EIRL': 6, 'NATURAL': 3}},
        'comprobantes': {'max': 10, 'factura': 5, 'electronico': 5},
        'logistica': {'max': 10, 'ubigeo_prefixes': ['15', '07']},
    },
    'tiers': {'A': 75, 'B': 55, 'C': 35},
    'tier_caps': [
        {'when': {'antiguedad_years_lt': 5}, 'max_tier': 'B'},  # D-13: con menos de 5 años no se descarta, pero no pasa de B
        {'when': {'rubro_points_lt': 1}, 'max_tier': 'C'},      # D-22 (P4): sin ningún punto de rubro no pasa de C
    ],
    'ciiu_weights': CIIU_WEIGHTS_SMARTPHONES,
}

PROFILE_V2_PADRONES = copy.deepcopy(PROFILE_V1)
PROFILE_V2_PADRONES['version'] = 2
del PROFILE_V2_PADRONES['criteria']['comprobantes']
PROFILE_V2_PADRONES['criteria']['padrones'] = {'max': 10, 'buen_contribuyente': 6, 'agente_retencion_igv': 4}

TIER_ORDER = ['A', 'B', 'C', 'D']  # de mejor a peor


def round_half_up(x: float) -> int:
    return int(x + 0.5)


def validate_profile(profile: dict) -> List[str]:
    """Devuelve la lista de problemas del perfil (vacía si está bien)."""
    problems = []
    total = sum(c['max'] for c in profile['criteria'].values())
    if total != 100:
        problems.append(f'los máximos suman {total}, deben sumar 100')
    t = profile['tiers']
    if not (t['A'] > t['B'] > t['C'] > 0):
        problems.append('los umbrales de nivel deben ser A > B > C > 0')
    for code, w in profile.get('ciiu_weights', {}).items():
        if not (0 <= w <= 1):
            problems.append(f'peso fuera de 0 a 1 en CIIU {code}')
    for cap in profile.get('tier_caps', []):
        if len(cap.get('when', {})) != 1 or not set(cap['when']) <= {'antiguedad_years_lt', 'rubro_points_lt'}:
            problems.append(f"tope con condición desconocida: {cap.get('when')}")
        if cap.get('max_tier') not in TIER_ORDER:
            problems.append(f"tope con nivel máximo inválido: {cap.get('max_tier')}")
    return problems


_PADRON_RE = re.compile(r'^(Incorporado|Excluido)\s+(?:al|del)\s+Régimen\s+de\s+(.+?)\s+a partir del\s+(\d{2})/(\d{2})/(\d{4})\s*$')


def padrones_vigentes(lines: List[str]) -> List[str]:
    """Regímenes en los que el contribuyente sigue incorporado: gana la línea más reciente de cada régimen
    (si el mismo día hay «Incorporado» y «Excluido», gana «Excluido»)."""
    last: Dict[str, tuple] = {}
    for line in lines:
        m = _PADRON_RE.match(line.strip())
        if not m:
            continue
        accion, regimen, d, mth, y = m.groups()
        regimen = re.sub(r'\s*\([^)]*\)', '', regimen).strip()  # quita «(Resolución N° …)» y «(R.S.…)»
        key = (int(y), int(mth), int(d), 1 if accion == 'Excluido' else 0)
        if regimen not in last or key > last[regimen][0]:
            last[regimen] = (key, accion)
    return sorted(r for r, (_, accion) in last.items() if accion == 'Incorporado')


def _gate(facts: dict, profile: dict) -> Optional[str]:
    g = profile['gates']
    if facts.get('excluido'):
        return 'excluido_manualmente'
    if facts.get('estado') not in g['estado']:
        return 'estado'
    if facts.get('condicion') not in g['condicion']:
        return 'condicion'
    if not set(g['comercio_exterior_requiere']) & set(facts.get('comercio_exterior') or []):
        return 'comercio_exterior'
    return None


def _item(key: str, points: int, maximum: int, note: str) -> dict:
    return {'key': key, 'points': points, 'max': maximum, 'note': note}


def score(facts: dict, profile: dict) -> dict:
    gate = _gate(facts, profile)
    if gate:
        return {'gate': gate, 'score': None, 'tier': None, 'items': [], 'tier_cap': None,
                'profile_version': profile['version']}
    crit = profile['criteria']
    items = []
    weights = profile.get('ciiu_weights', {})

    if 'rubro' in crit:
        c = crit['rubro']
        best, why = 0.0, 'sin código relevante'
        for a in facts.get('actividades') or []:
            w = weights.get(a['ciiu_code'], 0.0) * (1.0 if a['kind'] == 'PRINCIPAL' else c['secondary_factor'])
            if w > best:
                best = w
                why = f"{a['ciiu_code']} {'principal' if a['kind'] == 'PRINCIPAL' else 'secundaria'}, peso {weights[a['ciiu_code']]}"
        items.append(_item('rubro', round_half_up(c['max'] * best), c['max'], why))

    years = facts.get('antiguedad_anios')
    if 'antiguedad' in crit:
        c = crit['antiguedad']
        pts = 0
        if years is not None:
            for s in sorted(c['steps'], key=lambda s: s['min_years']):
                if years >= s['min_years']:
                    pts = s['points']
        items.append(_item('antiguedad', pts, c['max'], 'sin dato' if years is None else f'{years} años'))

    if 'forma_societaria' in crit:
        c = crit['forma_societaria']
        forma = facts.get('forma_societaria') or 'OTRA'
        items.append(_item('forma_societaria', c['values'].get(forma, 0), c['max'], forma))

    if 'comprobantes' in crit:
        c = crit['comprobantes']
        pts = (c['factura'] if facts.get('emite_factura') else 0) + (c['electronico'] if facts.get('emisor_electronico') else 0)
        items.append(_item('comprobantes', pts, c['max'],
                           f"factura {'sí' if facts.get('emite_factura') else 'no'}, emisor electrónico {'sí' if facts.get('emisor_electronico') else 'no'}"))

    if 'padrones' in crit:
        c = crit['padrones']
        vig = padrones_vigentes(facts.get('padrones') or [])
        bc = any(r == 'Buenos Contribuyentes' for r in vig)
        ar = any(r == 'Agentes de Retención de IGV' for r in vig)
        items.append(_item('padrones', (c['buen_contribuyente'] if bc else 0) + (c['agente_retencion_igv'] if ar else 0), c['max'],
                           f"buen contribuyente {'sí' if bc else 'no'}, agente de retención IGV {'sí' if ar else 'no'}"))

    if 'logistica' in crit:
        c = crit['logistica']
        ub = facts.get('ubigeo') or ''
        ok = len(ub) == 6 and ub[:2] in c['ubigeo_prefixes']
        items.append(_item('logistica', c['max'] if ok else 0, c['max'], f'ubigeo {ub[:2]}' if len(ub) == 6 else 'sin ubigeo'))

    total = sum(i['points'] for i in items)
    t = profile['tiers']
    tier = 'A' if total >= t['A'] else 'B' if total >= t['B'] else 'C' if total >= t['C'] else 'D'
    # Topes de nivel: limitan el nivel sin tocar el puntaje. Se aplican en el orden del perfil; `tier_cap` dice qué regla fijó
    # el nivel final y `caps_triggered` lista todas las que se cumplieron (aunque no bajaran el nivel).
    rubro_pts = next((i['points'] for i in items if i['key'] == 'rubro'), None)
    tier_before, cap_applied, triggered = tier, None, []
    for cap in profile.get('tier_caps', []):
        w = cap['when']
        rule = None
        if 'antiguedad_years_lt' in w and (years is None or years < w['antiguedad_years_lt']):
            rule = f"antiguedad_years_lt_{w['antiguedad_years_lt']}"
        elif 'rubro_points_lt' in w and rubro_pts is not None and rubro_pts < w['rubro_points_lt']:
            rule = f"rubro_points_lt_{w['rubro_points_lt']}"
        if rule is None:
            continue
        triggered.append(rule)
        if TIER_ORDER.index(tier) < TIER_ORDER.index(cap['max_tier']):
            tier = cap['max_tier']
            cap_applied = {'rule': rule, 'from': tier_before, 'to': tier}
    return {'gate': None, 'score': total, 'tier': tier, 'items': items, 'tier_cap': cap_applied,
            'caps_triggered': triggered, 'profile_version': profile['version']}


def facts_from_ficha(f: dict, antiguedad_anios: Optional[float], ubigeo: Optional[str] = None, excluido: bool = False) -> dict:
    """Arma los «hechos» que necesita score() a partir de una ficha leída por parse_ficha.parse_ficha()."""
    factura = 'FACTURA' in f['comprobantes_autorizados'] or any(e['tipo'].startswith('FACTURA') for e in f['comprobantes_electronicos'])
    return {'estado': f['estado'], 'condicion': f['condicion'], 'comercio_exterior': f['comercio_exterior'],
            'actividades': f['actividades'], 'antiguedad_anios': antiguedad_anios,
            'forma_societaria': f['forma_societaria'], 'emite_factura': factura,
            'emisor_electronico': bool(f['emisor_electronico_desde']), 'ubigeo': ubigeo,
            'padrones': f['padrones'], 'excluido': excluido}
