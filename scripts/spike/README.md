# Scripts del spike (semana 1)

Scripts **desechables** que produjeron las cifras de [`docs/12-informe-del-spike.md`](../../docs/12-informe-del-spike.md). Se reemplazan por el comando `radar` cuando exista el código del producto (`docs/11` §5). No contienen datos: las entradas viven en `data/` (fuera de git).

Se ejecutan con `python3 -I` (modo aislado) y reciben las rutas como argumentos. Solo usan la biblioteca estándar.

| Script | Para qué | Argumentos |
| --- | --- | --- |
| `padron_stats.py` | Formato, codificación y conteos del padrón reducido (en streaming, sin descomprimir a disco) | `padron_reducido_ruc.zip` |
| `aduanet_stats.py` | Filas, duplicados, RUC inválidos y fechas de la lista de Aduanet. Escribe los RUC únicos **sin nombres** | `lista.html` `rucs.tsv` |
| `padron_cross.py` | Cruza los RUC de la lista con el padrón y cuenta ACTIVO + HABIDO. Escribe los elegibles **sin nombres** | `padron.zip` `rucs.tsv` `elegibles.tsv` |
| `export_h1_csv.py` | Genera el CSV de importadores `ACTIVO` + `HABIDO` con razón social, tipo, estado, condición, departamento y prioridad | `lista.html` `elegibles.tsv` `salida.csv` |

## Orden de uso

```bash
python3 -I scripts/spike/aduanet_stats.py data/raw/aduanet/<fecha>/lista.html data/processed/aduanet/<fecha>/rucs.tsv
python3 -I scripts/spike/padron_cross.py data/raw/padron/<fecha>/padron_reducido_ruc.zip \
    data/processed/aduanet/<fecha>/rucs.tsv data/processed/aduanet/<fecha>/rucs_activo_habido.tsv
python3 -I scripts/spike/export_h1_csv.py data/raw/aduanet/<fecha>/lista.html \
    data/processed/aduanet/<fecha>/rucs_activo_habido.tsv data/processed/aduanet/<fecha>/importadores_activo_habido.csv
```

## Cuidado con los datos

- Los archivos de `data/` incluyen **RUC de personas naturales** (llevan el DNI) y nombres de personas. No los subas a git, a la nube ni los compartas.
- Los archivos descargados se tratan como no confiables: se leen solo con estos scripts, sin ejecutarlos ni abrirlos con intérpretes desde su carpeta.
