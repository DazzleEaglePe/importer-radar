# Scripts del spike (semana 1)

Scripts **desechables** que produjeron las cifras de [`docs/12-informe-del-spike.md`](../../docs/12-informe-del-spike.md). Se reemplazan por el comando `radar` cuando exista el código del producto (`docs/11` §5). No contienen datos: las entradas viven en `data/` (fuera de git).

Se ejecutan con `python3 -I` (modo aislado) y reciben las rutas como argumentos. Solo usan la biblioteca estándar.

| Script | Para qué | Argumentos |
| --- | --- | --- |
| `padron_stats.py` | Formato, codificación y conteos del padrón reducido (en streaming, sin descomprimir a disco) | `padron_reducido_ruc.zip` |
| `aduanet_stats.py` | Filas, duplicados, RUC inválidos y fechas de la lista de Aduanet. Escribe los RUC únicos **sin nombres** | `lista.html` `rucs.tsv` |
| `padron_cross.py` | Cruza los RUC de la lista con el padrón y cuenta ACTIVO + HABIDO. Escribe los elegibles **sin nombres** | `padron.zip` `rucs.tsv` `elegibles.tsv` |
| `pick_sp06_sample.py` | Arma la muestra de 20 RUC variados (S.A.C., S.A., E.I.R.L., S.R.L., sucursal, con y sin palabras clave, Lima y provincias, 2 personas naturales) para las consultas manuales | `importadores_activo_habido.csv` `salida.csv` |
| `lookup_fetch.py` | **Consulta RUC automática** con tu Chrome: abre la consulta de SUNAT, busca cada RUC y guarda la ficha. Ritmo cortés, topes, reanudable. **Lo lanzas tú** (ver abajo) | `--list` `--out` `--max` … |
| `test_lookup_fetch.py` | 16 pruebas de la lógica de `lookup_fetch.py` con un navegador simulado (no toca SUNAT) | — |
| `test_lookup_browser.py` | 13 pruebas del **navegador real** (tu Chrome) contra una página **local** que imita el formulario y la ficha: iframe, respuesta lenta, sin resultado, verificación, bloqueo, ficha que no aparece. No toca SUNAT | — |
| `requirements.txt` | Versión fijada de Playwright | — |
| `parse_ficha.py` | **Parser de las fichas** guardadas: extrae los campos de la consulta RUC y los valida (si falta un campo obligatorio, la ficha se reporta como error y no se acepta). Opcionalmente escribe un CSV sin datos personales | `carpeta_de_fichas` `--csv salida.csv` |
| `test_parse_ficha.py` | 17 pruebas del parser con fichas inventadas de la misma estructura que las reales. Si existen fichas reales en `data/`, comprueba además que todas se lean | — |
| `export_h1_csv.py` | Genera el CSV de importadores `ACTIVO` + `HABIDO` con razón social, tipo, estado, condición, departamento y prioridad | `lista.html` `elegibles.tsv` `salida.csv` |

## Orden de uso

```bash
python3 -I scripts/spike/aduanet_stats.py data/raw/aduanet/<fecha>/lista.html data/processed/aduanet/<fecha>/rucs.tsv
python3 -I scripts/spike/padron_cross.py data/raw/padron/<fecha>/padron_reducido_ruc.zip \
    data/processed/aduanet/<fecha>/rucs.tsv data/processed/aduanet/<fecha>/rucs_activo_habido.tsv
python3 -I scripts/spike/export_h1_csv.py data/raw/aduanet/<fecha>/lista.html \
    data/processed/aduanet/<fecha>/rucs_activo_habido.tsv data/processed/aduanet/<fecha>/importadores_activo_habido.csv
```

## Consulta RUC automática (`lookup_fetch.py`)

Preparación, una sola vez, dentro de `bot-scraping/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/spike/requirements.txt   # Playwright 1.60.0. Usa tu Chrome instalado: no descarga otro navegador
```

El entorno ocupa unos 142 MB en `.venv/` (fuera de git). Si ya existe, no hace falta repetirlo.

Primera corrida (muestra de 20 + la ficha de baja; Chrome visible y una captura por ficha):

```bash
.venv/bin/python -I scripts/spike/lookup_fetch.py \
    --list data/processed/aduanet/2026-10-25/sp06_muestra_20_ruc.csv --ruc 20526185847 \
    --out data/raw/consulta_ruc/2026-10-25 --max 21 --screenshot
```

Un día de trabajo (los 400 de mayor prioridad que falten; es reanudable y se puede repetir al día siguiente):

```bash
.venv/bin/python -I scripts/spike/lookup_fetch.py \
    --list data/processed/aduanet/2026-10-25/importadores_activo_habido.csv \
    --out data/raw/consulta_ruc/2026-10-25 --max 400
```

`--dry-run` muestra el plan sin abrir el navegador. `--form-url` solo acepta direcciones locales y sirve para pruebas.

Pruebas (no tocan SUNAT):

```bash
python3 -I scripts/spike/test_lookup_fetch.py            # lógica, con un navegador simulado
.venv/bin/python -I scripts/spike/test_lookup_browser.py  # navegador real contra una página local (~45 s)
```

## Cuidado con los datos

- Los archivos de `data/` incluyen **RUC de personas naturales** (llevan el DNI) y nombres de personas. No los subas a git, a la nube ni los compartas.
- Los archivos descargados se tratan como no confiables: se leen solo con estos scripts, sin ejecutarlos ni abrirlos con intérpretes desde su carpeta.
