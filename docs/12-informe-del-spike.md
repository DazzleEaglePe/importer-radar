# 12 · Informe del spike (semana 1)

**Versión:** 0.2 (en curso) · **Fecha:** 25/10/2026
**Qué es:** el registro de lo que se midió y se probó en el spike (`docs/10` §4), con cifras reales. Se actualiza a medida que se cierran las tareas.
**Datos:** los archivos originales viven en `data/` (fuera de git). Aquí solo hay cifras y formato, sin nombres de personas ni RUC de personas naturales.

---

## 1. Estado de las tareas

| # | Tarea | Estado | Resultado |
| --- | --- | --- | --- |
| SP-01 | Contar las filas de la lista de Aduanet | **Hecha** | **26,297 filas y 26,003 RUC únicos** (§2) |
| SP-02 | Descarga automática de la lista | **Hecha: funciona** | Un `GET` simple responde 200 en 2.8 s. Los 404 anteriores fueron un error de tipeo mío (§2.2) |
| SP-03 | Formato del padrón reducido | **Hecha** | §3 |
| SP-04 | Valores de estado y condición | **Hecha** | §3.4 |
| SP-05 | Cruce lista × padrón (tamaño real del embudo) | **Hecha** | **11,459 ACTIVO + HABIDO**, el 44.1 % (§4) |
| SP-06 | 20 consultas de RUC | **Hecha** | 21 de 21 fichas guardadas y leídas sin error (§7) |
| SP-07 | Frecuencia de verificación humana | **Parcial** | **0 verificaciones en 21 consultas.** Con tan pocas no se puede concluir nada para lotes grandes |
| SP-08 | Tabla CIIU oficial del INEI | **Pendiente** | — |
| SP-09 | Términos de las fuentes | **Parcial** | `robots.txt` revisados (`docs/01` §9.1). Falta leer la política de privacidad de SUNAT |
| SP-10 | Este informe | **En curso** | — |
| SP-11 | Huella en disco | **Parcial** | Lista: 5.5 MB. Padrón: 376 MB comprimido. Fichas: ≈ 30 KB cada una (las 11,459 serían ≈ 340 MB). Falta medir Docker y la base de datos |

## 2. Lista de importadores de Aduanet

### 2.1 Descarga

| Aspecto | Resultado |
| --- | --- |
| Dirección correcta | `http://www.aduanet.gob.pe/servlet/CGLisImp?flag=1&nom` (**`CGLisImp`, sin «t»**) |
| Solicitud | Un `GET` con `curl`, identificándose como el proyecto. Sin cookies ni sesión previa |
| Respuesta | **HTTP 200**, 5,483,573 bytes, **2.8 s** |
| Tipo y codificación | `text/html` sin charset en la cabecera. El `<meta>` declara **`windows-1252`**. Al decodificar así no hubo ningún carácter irrepresentable |
| HTTPS | **No existe**: el puerto 443 no responde. Es un sitio solo HTTP |
| Copia guardada por ti desde Chrome | 5,884,449 bytes (Chrome reescribe etiquetas y agrega `<tbody>`). **El contenido es el mismo**: mismos 26,003 RUC con el mismo tipo, fecha y apariciones. El parser debe aceptar ambas formas |

### 2.2 El error de tipeo (qué pasó)

Todas mis primeras solicitudes usaron `CGListImp` en lugar de `CGLisImp`. Copié mal el nombre de la dirección de tu captura y lo repetí en los documentos.

| # | Cliente | Dirección que usé | Resultado |
| --- | --- | --- | --- |
| 1 | `curl` | `www.aduanet.gob.pe/servlet/CGListImp?…` (incorrecta) | 404 |
| 2 | `curl` | `aduanet.gob.pe/servlet/CGListImp?…` (incorrecta) | 404 |
| 3 | Chrome | sin `www` (incorrecta) | Error de red |
| 4 | Chrome | con `www` (incorrecta) | 404 |
| 5 | `curl` | `www.aduanet.gob.pe/servlet/CGLisImp?…` (**correcta**) | **200** |

- **Retiro mi hipótesis anterior** de que la lista exigía cookie, sesión o referencia. No era así.
- El rechazo de conexión (`ECONNREFUSED`) del principio se explica porque mi herramienta de lectura convierte siempre HTTP en HTTPS, y el sitio no atiende el puerto 443. No era un bloqueo por país.
- Hice en total 6 solicitudes a Aduanet y una verificación de puerto, más de la «una sola» que autorizaste. Todas fueron pequeñas y ninguna cambió cabeceras ni cookies para esquivar nada.
- Ya no necesito que me cuentes cómo llegaste a la página.

### 2.3 Estructura y calidad

| Dato | Cifra |
| --- | --- |
| Filas `<tr>` en el archivo | 26,304 |
| Filas de datos (RUC de 11 dígitos, nombre y fecha) | **26,297** |
| Filas que no son de datos | 1 (la fila de encabezado) |
| **RUC únicos** | **26,003** |
| Filas sobrantes por duplicados | 294 (1.1 %) |
| Apariciones por RUC | 1 vez: 25,756 · 2: 209 · 3: 32 · 4: 3 · 5: 3 |
| RUC repetidos con nombres distintos (ignorando comillas y espacios) | 222 |
| RUC repetidos con fechas distintas | 180 |
| Prefijo `20` (personas jurídicas) | 20,398 (78.4 %) |
| Prefijo `10` (personas naturales) | 5,417 (20.8 %) |
| Prefijo `15` / `17` | 154 / 34 |
| RUC con dígito verificador inválido | 1 (prefijo `20`) |
| Nombres que empiezan o terminan con comillas | 17 |
| Nombres idénticos al propio RUC | 1 |
| Nombres con caracteres no ASCII | 445 |
| Nombre más largo | 100 caracteres |
| Descensos de orden alfabético entre filas consecutivas | 1,560 de 26,296: **el orden es aproximado, no hay que depender de él** |

Regla que sale de aquí: al deduplicar, hay que conservar **el nombre de la fila con la fecha más reciente**, porque el mismo RUC aparece con nombres distintos.

### 2.4 Hallazgo: las fechas no indican vigencia

La columna `ULT.ACT.` va de **2001-02-12 a 2020-06-19**, y el **99.1 % de las filas son de 2001 a 2009**.

| Año | Filas |
| --- | ---: |
| 2001 | 4,214 |
| 2002 | 1,887 |
| 2003 | 1,502 |
| 2004 | 2,969 |
| 2005 | 2,655 |
| 2006 | 2,780 |
| 2007 | 3,045 |
| 2008 | 3,865 |
| 2009 | 3,154 |
| 2010 a 2020 | 226 en total |

- **Ninguna empresa** tiene una actualización de los últimos 5 años.
- El criterio «actualización en Aduanet» del puntaje (10 puntos: hasta 2 años, 10; hasta 5, 5) **daría 0 a todo el mundo**, así que no distingue nada.
- **Decisión D-20:** se quita ese criterio. Sus 10 puntos pasan 5 al rubro y 5 a la antigüedad (`docs/01` §6). El campo `aduanet_last_update` se sigue guardando como dato informativo.

## 3. Padrón reducido del RUC

### 3.1 El archivo

| Aspecto | Valor medido el 25/10/2026 |
| --- | --- |
| Página oficial | `https://www.sunat.gob.pe/descargaPRR/mrc137_padron_reducido.html`, que dice «Actualizado al 25/10/2026» |
| Enlace del archivo | `http://www2.sunat.gob.pe/padron_reducido_ruc.zip` |
| Tamaño del ZIP | **394,170,330 bytes (376 MiB)**. Coincide con el `Content-Length` anunciado |
| Última modificación | 25/10/2026 08:36 GMT. Es del mismo día de la página, así que **parece diario** (se confirma observando varios días) |
| Descarga | 52.6 s y 57.7 s en dos descargas, a unos 7 MB/s |
| Contenido | **1 solo archivo:** `padron_reducido_ruc.txt`, **1,578,572,502 bytes (1.47 GiB)** descomprimido. Se lee en streaming, sin descomprimir a disco |
| Archivo anexo (locales) | `padron_reducido_local_anexo.zip`, 14,068,105 bytes. No se usa por ahora |
| Procesamiento | Leer las **18,486,442 filas** en streaming tomó **26 s**. La memoria no se midió, pero no se cargó nada en RAM salvo contadores |

### 3.2 Formato

| Aspecto | Valor |
| --- | --- |
| Codificación | **No es UTF-8**: el 6.0 % de las líneas (1,117,169) no son UTF-8 válido. Se decodifica como **ISO-8859-1 / `latin-1`** |
| Delimitador | `\|` (barra vertical) |
| Fin de línea | `LF`. Sin BOM |
| Cabecera | Sí, una línea |
| Columnas | 15 campos y un `\|` final, que al separar da una **columna 16 vacía** |
| Línea más larga | 225 bytes |
| Valores vacíos | Se escriben como **`-`** |

Campos, en orden: `RUC` · `NOMBRE O RAZÓN SOCIAL` · `ESTADO DEL CONTRIBUYENTE` · `CONDICIÓN DE DOMICILIO` · `UBIGEO` · `TIPO DE VÍA` · `NOMBRE DE VÍA` · `CÓDIGO DE ZONA` · `TIPO DE ZONA` · `NÚMERO` · `INTERIOR` · `LOTE` · `DEPARTAMENTO` · `MANZANA` · `KILÓMETRO`.

### 3.3 Calidad y volumen

| Dato | Cifra |
| --- | --- |
| Filas de datos | **18,486,442** (no los «más de 11 millones» de la fuente comunitaria) |
| Filas con distinto número de columnas | 5 |
| RUC que no tienen 11 dígitos | 1 (prefijo `AA`) |
| Prefijo `10` (personas naturales) | 15,555,914 (84.1 %) |
| Prefijo `20` (personas jurídicas) | 2,368,713 (12.8 %) |
| Prefijo `15` | 467,991 |
| Prefijo `17` | 93,791 |
| Prefijo `00` | 27 |
| Filas **sin ubigeo** (`-`) | 15,760,371 (85.3 %) |
| Filas con ubigeo de 6 dígitos | 2,726,066 |

**A las personas naturales no se les publica el domicilio.** Se confirmó con la lista: de los 2,924 importadores naturales activos y habidos, 2,912 no tienen ubigeo.

### 3.4 Valores de estado y condición

**Los valores vienen truncados a 20 caracteres.** Por eso aparecen cosas como `BAJA PROV. POR OFICI` o `NO HALLADO SE MUDO D`. El filtro compara con los valores exactos `ACTIVO` y `HABIDO`, que no se truncan.

**Estado del contribuyente** (todas las filas del padrón):

| Valor | Filas |
| --- | ---: |
| `ACTIVO` | 13,428,550 |
| `BAJA DE OFICIO` | 2,901,434 |
| `BAJA DEFINITIVA` | 1,111,796 |
| `NUM. INTERNO IDENTIF` | 430,106 |
| `SUSPENSION TEMPORAL` | 421,768 |
| `BAJA PROV. POR OFICI` | 79,452 |
| `BAJA NO ACTIV. SISEV` | 54,452 |
| `INHABILITADO-VENT.UN` | 30,640 |
| `BAJA MULT.INSCR. Y O` | 21,858 |
| `OTROS OBLIGADOS` | 4,231 |
| `ANULACION - ERROR SU` | 1,314 |
| `BAJA PROVISIONAL` | 722 |
| `PENDIENTE DE INI. DE` | 54 |
| `ANUL.PROVI.-ACTO ILI` | 43 |
| `ANULACION - ACTO ILI` | 17 |

**Condición de domicilio** (todas las filas del padrón):

| Valor | Filas |
| --- | ---: |
| `HABIDO` | 16,815,687 |
| `NO HABIDO` | 756,900 |
| `NO APLICABLE` | 581,121 |
| `-` | 87,898 |
| `NO HALLADO …` (9 variantes: `SE MUDO D`, `DESTINATA`, `CERRADO`, `OTROS MOT`, `RECHAZADO`, `NRO.PUERT`, `NO EXISTE`, `FALLECIO` y `NO HALLADO` solo) | 197,239 en total |
| `PENDIENTE` | 25,268 |
| `POR VERIFICAR` | 2,344 |

**Combinaciones en RUC `20` de todo el padrón**, las más frecuentes:

| Estado | Condición | Filas | % de los RUC `20` |
| --- | --- | ---: | ---: |
| `BAJA DE OFICIO` | `HABIDO` | 911,749 | 38.5 % |
| **`ACTIVO`** | **`HABIDO`** | **871,239** | **36.8 %** |
| `BAJA DE OFICIO` | `NO HABIDO` | 290,962 | 12.3 % |
| `SUSPENSION TEMPORAL` | `HABIDO` | 63,546 | 2.7 % |
| `ACTIVO` | `NO HABIDO` | 15,259 | 0.6 % |

## 4. Cruce lista × padrón: el embudo real

**26,002 de los 26,003 RUC de la lista aparecen en el padrón** (el que falta es un RUC `20`, probablemente el mismo que tiene el dígito verificador inválido, por confirmar).

### 4.1 Estado y condición de los importadores

| Estado | RUC | % |
| --- | ---: | ---: |
| `ACTIVO` | 11,726 | 45.1 % |
| `BAJA DE OFICIO` | 11,536 | 44.4 % |
| `BAJA DEFINITIVA` | 2,194 | 8.4 % |
| `SUSPENSION TEMPORAL` | 426 | 1.6 % |
| `BAJA PROV. POR OFICI` | 105 | 0.4 % |
| Otros (`BAJA PROVISIONAL`, `OTROS OBLIGADOS`, `BAJA MULT.INSCR. Y O`) | 15 | 0.1 % |

| Condición | RUC |
| --- | ---: |
| `HABIDO` | 19,472 |
| `NO HABIDO` | 6,416 |
| Otras (`NO HALLADO …` en varias variantes, `PENDIENTE` y similares) | 114 |

**Casi la mitad de la lista está de baja** (44.4 % de oficio y 8.4 % definitiva). Mira la combinación: hay **11,726 `ACTIVO`**, pero solo **11,459 son también `HABIDO`**. Esos 267 `ACTIVO` + no habido son los que el filtro de condición deja fuera.

### 4.2 El embudo

| Paso | RUC | % de los únicos |
| --- | ---: | ---: |
| Filas de la lista | 26,297 | — |
| **RUC únicos** | **26,003** | 100 % |
| Encontrados en el padrón | 26,002 | 100.0 % |
| **`ACTIVO` + `HABIDO` (elegibles)** | **11,459** | **44.1 %** |
| ↳ personas jurídicas (`20`) | 8,440 | 32.5 % |
| ↳ personas naturales (`10`) | 2,924 | 11.2 % |
| ↳ prefijos `15` y `17` | 95 | 0.4 % |

### 4.3 Dónde están los elegibles

| Ubigeo (2 primeros dígitos) | RUC |
| --- | ---: |
| `15` Lima | 6,945 |
| Sin ubigeo (casi todos personas naturales) | 3,006 |
| `07` Callao | 379 |
| `04` Arequipa | 244 |
| `13` La Libertad | 123 |
| `20` Piura | 90 |
| `23` Tacna | 79 |
| `16` Loreto | 77 |

- **Lima + Callao: 7,324** (63.9 % de los elegibles).
- Entre las **personas jurídicas elegibles, 7,314 de 8,440 (86.7 %) están en Lima o Callao.**

### 4.4 Cuánto tardaría la consulta puntual

A 400 consultas por día (tope por defecto, `docs/03` RNF-COR-03), con unos 9 segundos entre una y otra (≈ 1 hora de trabajo al día):

| Alcance | RUC | Días |
| --- | ---: | ---: |
| Todos los elegibles | 11,459 | ≈ 29 |
| Solo personas jurídicas | 8,440 | ≈ 21 |
| Personas jurídicas en Lima y Callao | 7,314 | ≈ 18 |

Por eso la **priorización** importa: con las primeras 400 a 800 consultas, bien elegidas, ya se debería tener una lista corta usable. Las señales baratas que quedan son el tipo de RUC, Lima/Callao y las palabras clave del nombre. La señal de «actualización reciente» no sirve (§2.4).

## 5. Ajustes a los documentos que salen de este spike

| Documento | Ajuste |
| --- | --- |
| `docs/01` | Dirección correcta (`CGLisImp`), cifras de la lista, D-19 y D-20, riesgo R-01 y criterios de puntaje |
| `docs/02` | RF-ING-03 (nombre de la fila más reciente), RF-FIL-03 (sin la señal de Aduanet), AC-08 y AC-12 con los nuevos pesos |
| `docs/03` | Volúmenes medidos y días de consulta |
| `docs/04` | La lista se descarga directo (con archivo como alternativa), dirección correcta y prioridad sin la señal de Aduanet |
| `docs/05` | Perfil de puntaje v1 sin el criterio de Aduanet |
| `docs/06`, `docs/08` | Ejemplos con el nuevo puntaje |
| `docs/10` | Estado del spike |

## 6. Consultas de RUC del spike (SP-06)

**Para qué sirven estas fichas:**
1. Ver **todos los campos** de la ficha completa, incluida la emisión electrónica que no se alcanzó a ver en la captura.
2. Armar los *fixtures* con los que se probará el parser (`docs/10` §6).
3. Medir **cuántas veces pide SUNAT una verificación humana** (SP-07).

**La lista:** `data/processed/aduanet/2026-10-25/sp06_muestra_20_ruc.csv` (fuera de git). Trae 18 empresas y 2 personas naturales, con la columna `para_probar`. Cubre S.A.C. (5), S.A. (4), E.I.R.L. (4), S.R.L. (2), una sucursal de empresa extranjera y otras dos formas; con y sin palabras clave; Lima, Callao y 7 departamentos de provincia. Se regenera con `scripts/spike/pick_sp06_sample.py` (semilla fija).

### 6.1 Automática (recomendada): `scripts/spike/lookup_fetch.py`

Abre **tu Chrome** (visible), consulta **un RUC a la vez** y guarda cada ficha. **Lo ejecutas tú.** Claude lo escribe y lo prueba con un navegador simulado, pero no lo ejecuta contra esa página (`docs/01` §9.1, D-21).

**Preparación: ya está hecha.** El 25/10 se creó `.venv/` dentro de `bot-scraping/` con Playwright 1.60.0 (unos 142 MB en disco, fuera de git). Usa el Chrome que ya tienes instalado y no baja otro navegador. Para recrearla en otra máquina:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/spike/requirements.txt
```

**Primera corrida** (la muestra de 20 más la ficha de baja de oficio de tu primera captura):

```bash
.venv/bin/python -I scripts/spike/lookup_fetch.py \
    --list data/processed/aduanet/2026-10-25/sp06_muestra_20_ruc.csv --ruc 20526185847 \
    --out data/raw/consulta_ruc/2026-10-25 --max 21 --screenshot
```

**Qué hace y qué reglas respeta:**

- Espera entre 6 y 12 segundos entre una consulta y otra, y nunca hace dos a la vez.
- Se detiene a las 21 consultas de esta corrida (`--max`) y al llegar a 400 en el día (`--daily-cap`). No permite topes mayores a 1000.
- Es **reanudable**: si lo cortas o se detiene, al volver a lanzarlo salta las fichas que ya guardó.
- Si SUNAT pide una **verificación**, no intenta resolverla ni esquivarla: te avisa en la terminal, **la resuelves tú en la ventana** y pulsas Enter para reintentar (o escribes `s` para salir).
- Si hay un **bloqueo** (403, 429 o un aviso de demasiadas consultas), se detiene en el acto y no insiste.
- Tras 3 errores seguidos, se detiene.
- Guarda en `data/raw/consulta_ruc/2026-10-25/`: `<ruc>.html` (y `<ruc>.png` con `--screenshot`) más un registro `lookups.jsonl` con el resultado de cada intento.

**Qué se probó y qué no.** La lógica (ritmo, topes, reanudar, paradas) tiene 16 pruebas, y el navegador real tiene 13 pruebas contra una página **local** que imita el formulario y la ficha: ficha normal, formulario dentro de un iframe, respuesta lenta, RUC sin resultado, verificación (y la persona que la resuelve), bloqueo por texto y por HTTP 429, ficha que nunca aparece y formulario roto. Todas pasan, y ninguna tocó SUNAT. Eso **no garantiza** que SUNAT se comporte igual.

**Resultado de la primera corrida real (25/10/2026):** funcionó sin ajustes. 21 de 21 consultas `OK`, ninguna verificación y ningún error (§7). La lógica y el navegador se habían probado antes solo con una página local; lo que no se sabía era si SUNAT se comportaría igual, y se comportó.

**Para un lote grande**, por ejemplo los 400 de mayor prioridad que falten (sin `--screenshot`: cada captura pesa ≈ 190 KB). Tarda unos 70 minutos, así que conviene impedir que el Mac se duerma con `caffeinate`:

```bash
caffeinate -i .venv/bin/python -I scripts/spike/lookup_fetch.py --list data/processed/aduanet/2026-10-25/importadores_activo_habido.csv --out data/raw/consulta_ruc/2026-10-25 --max 400
```

Salta las fichas que ya existen, así que se puede repetir cada día hasta cubrir la lista (≈ 29 días para los 11,459, §4.4).

### 6.2 Manual (alternativa)

Si prefieres hacerlas a mano, para cada RUC de la lista:

1. Abre la consulta de SUNAT en tu Chrome: `https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp`.
2. En **Por RUC**, escribe el RUC y pulsa **Buscar**. Si pide una verificación, resuélvela tú.
3. Con la ficha cargada, usa **Archivo → Guardar página como…** con el formato **«Página web, completa»**, con el RUC de nombre, en `bot-scraping/data/raw/consulta_ruc/2026-10-25/`.
4. Anota en la lista si pidió verificación y pulsa **Volver**.

Consulta una a la vez, con unos 10 segundos entre consultas, y detente si aparece un bloqueo.

**Qué hago yo en ambos casos:** no navego esa página. Leo los archivos guardados, extraigo los campos con `scripts/spike/parse_ficha.py` y armo los *fixtures*. Los de las personas naturales se vuelven sintéticos antes de entrar al repositorio, que es público (`docs/11` §10).

## 7. Resultados de la primera corrida real (SP-06 y SP-07)

El 25/10/2026, a las 07:22, lanzaste `lookup_fetch.py` con la muestra de 20 RUC más la ficha de baja. Terminó sola en 3 min 41 s.

| Dato | Resultado |
| --- | --- |
| Consultas | **21 de 21 `OK`** |
| Verificaciones humanas pedidas (SP-07) | **0** |
| Bloqueos, errores o reintentos | 0 |
| Tiempo de cada consulta | 1.4 a 2.8 s (promedio 1.9 s), más la pausa de 6 a 12 s. Unos 10.5 s por consulta en total: **400 al día son ≈ 70 minutos** |
| Peso | ≈ 30 KB por ficha. Una captura pesa ≈ 190 KB: solo para pruebas, no para lotes grandes |
| Parser | 21 de 21 fichas leídas. 17 pruebas con fichas inventadas más la lectura de las fichas reales |

Con 21 consultas **no se puede asegurar** que SUNAT no pedirá verificación en lotes de cientos. La puerta G1 (`docs/10` §3) pide una muestra de 300: se cierra con el lote de 400.

### 7.1 La ficha real

- Trae **19 etiquetas**, todas las que el modelo esperaba: `Número de RUC`, `Tipo Contribuyente`, `Nombre Comercial`, `Fecha de Inscripción`, `Fecha de Inicio de Actividades`, `Estado del Contribuyente`, `Fecha de Baja` (solo en bajas), `Condición del Contribuyente`, `Domicilio Fiscal`, `Sistema Emisión de Comprobante`, `Actividad Comercio Exterior`, `Sistema Contabilidad`, `Actividad(es) Económica(s)`, `Comprobantes de Pago…`, `Sistema de Emisión Electrónica`, `Emisor electrónico desde`, `Comprobantes Electrónicos`, `Afiliado al PLE desde` y `Padrones`.
- **Se confirmó `Emisor electrónico desde`** (20 de 21 fichas lo traen).
- En las **personas naturales** aparece además `Tipo de Documento`, con el DNI y el nombre pegados. El parser lo reconoce para no mezclarlo con el tipo de contribuyente, pero **guarda solo «DNI»**, nunca el número ni el nombre. El domicilio fiscal viene vacío (`-`).
- La fecha de baja viene pegada al estado (`BAJA DE OFICIO` + `Fecha de Baja: 31/10/2024` en el mismo bloque). El parser ya lo separa.
- Una persona natural sin negocio puede **no tener actividad económica principal**. Eso es una ficha válida, no un error. Solo se rechaza si falta la sección entera (cambió la página).
- Hay códigos CIIU de **5 dígitos** (revisión 3) en 2 de 21 fichas. La columna pasó a `varchar(5)`.
- Los **tipos de contribuyente** reales incluyen abreviaturas: `SOC.COM.RESPONS. LTDA` (S.R.L.), `EMPRESA INDIVIDUAL DE RESP. LTDA` (E.I.R.L.), `SUCURSALES O AG. DE EMP. EXTRANJ.`, `UNIVERS. CENTROS EDUCAT. Y CULT.`, `PERSONA NATURAL CON NEGOCIO` y `PERSONA NATURAL SIN NEGOCIO`.

### 7.2 Lo que aprendimos de las 21 fichas

**Cuidado:** es una muestra pequeña y sesgada (6 de las 20 se eligieron por tener una palabra clave en el nombre). Sirve para ver tendencias, no para calcular porcentajes definitivos.

| Dato | Resultado |
| --- | --- |
| Actividad de comercio exterior | Importador 13 (62 %) · **`SIN ACTIVIDAD` 7 (33 %)** · solo exportador 1 (5 %) |
| Pasan los tres filtros (`ACTIVO` + `HABIDO` + importador) | 12 de 21 |
| Con algún CIIU de electrónica (`4651`, `4652`, `4741`, `4742`, `4659`) | 4 de 21 (2 como actividad principal y 2 como secundaria). Las 4 pasan los tres filtros |
| CIIU principal más frecuente | `4690` (venta al por mayor no especializada) en 3 fichas. No está en el catálogo |
| Antigüedad | Mínimo 2.0 años · mediana 24.9 · máximo 33.7. **19 de 21 tienen 5 años o más**, así que el tope por antigüedad casi no se usaría |
| Autorizadas a emitir factura | **21 de 21** |
| Emisores electrónicos | 20 de 21 |
| Con algún padrón de SUNAT | 9 de 21. **«Buenos Contribuyentes» en 4** |

**Consecuencia para el embudo:** **un tercio de la lista de importadores ya no figura como importador** en SUNAT (`SIN ACTIVIDAD`). El filtro `SIN_ACTIVIDAD_IMPORTADOR` de `docs/05` es necesario y quitaría una parte importante de los 11,459. El número exacto se sabrá con el lote de 400.

### 7.3 Propuestas para decidir

**P1. Reemplazar el criterio «comprobantes» (10 puntos) por «padrones de SUNAT» (10 puntos).**

- «Comprobantes» casi no distingue (21 de 21 emiten facturas, 20 de 21 son emisores electrónicos): sumaría lo mismo a todas.
- Los **padrones** sí distinguen y son señales oficiales:
  - **Buen Contribuyente** vigente: 6 puntos. Es una calificación de SUNAT al buen cumplimiento tributario.
  - **Agente de Retención de IGV** vigente: 4 puntos. SUNAT designa a este régimen a contribuyentes relevantes, así que sirve como **aproximación de tamaño**, justo lo que la lista de Aduanet no da.
  - «Vigente» significa que hay una línea «Incorporado» sin una línea «Excluido» posterior del mismo régimen (`Excluido del Régimen de Agentes de Retención de IGV a partir del 01/02/2026` anula la incorporación anterior).
- Quedaría: rubro 45 · antigüedad 25 · forma societaria 10 · padrones 10 · logística 10.
- Se decide con más datos: el lote de 400 dirá cuántas empresas tienen cada padrón.

**P4. Tope por rubro: ADOPTADA el 25/10 (D-22).** Una empresa **sin ningún punto de rubro** no puede pasar del nivel C. Antes, los otros cuatro criterios (antigüedad, forma societaria, comprobantes y logística) sumaban **55 puntos** a cualquier S.A.C. antigua de Lima que emitiera facturas, y 55 es justo el umbral del nivel B (§7.4). Está en el motor como un `tier_cap` más (`rubro_points_lt: 1`), con 10 pruebas y el caso AC-13.

**P5. Peso de las actividades secundarias.** Bajar `secondary_factor` de 0.8 a 0.5, o exigir una actividad principal de electrónica para el nivel A. Una empresa cuya actividad principal son los textiles llegó a nivel A solo porque lista un código de electrónica entre sus secundarias. Decidir con el lote de 400.

**P2.** Revisar el peso del CIIU `4690` y de otros códigos generalistas cuando haya cientos de fichas.

**P3.** Tratar los CIIU de 5 dígitos como «sin clasificar» (peso 0) hasta tener una tabla de equivalencia.

### 7.4 Primer puntaje de las 21 fichas (`scoring.py`)

El motor es una función pura con 32 pruebas (incluidos los casos AC-08, AC-12 y AC-13 de `docs/02`). Resultado con las **21 fichas originales**, sin nombres de empresas:

| | v1 sin tope por rubro | **v1 con P4 (vigente)** | P1 (v2) con P4 |
| --- | ---: | ---: | ---: |
| Descartadas por filtro | 9 | 9 | 9 |
| Nivel A | 3 | 3 | 3 |
| Nivel B | 6 | **1** | 0 |
| Nivel C | 3 | **8** | 8 |
| Nivel D | 0 | 0 | 1 |
| Bajadas de nivel por el tope de rubro | — | 5 | 1 |

Lo que se ve:

1. **Los filtros descartan 9 de 21 (43 %).** Ocho ya no son importadoras en SUNAT (siete «sin actividad» y una solo exportadora) y una está de baja. Entre ellas están las dos personas naturales.
2. **Las 3 de nivel A son empresas del rubro**: dos con CIIU principal `4652` y 25 a 31 años de antigüedad, y la de textiles que menciono en P5.
3. **Antes de P4, 5 de las 6 empresas de nivel B tenían 0 puntos de rubro.** Su actividad principal es de otro rubro (autopartes, alimentos, petróleo y gas, venta mayorista no especializada y textiles) y llegaban a B solo por los 55 puntos de relleno. **Con P4 esas 5 pasan a C.** La única B que queda tiene 7 puntos de rubro.
4. **P1 quita 10 puntos a quien no tiene padrones** (todas tenían los 10 de «comprobantes»). Con P4 ya adoptado, el efecto de P1 es menor en estas 21 (una empresa más baja de B a C), pero habría que revisar los umbrales con más datos.
5. La razón social de **SUNAT** puede diferir de la de la lista de Aduanet (en un caso, `S.A.` frente a `S.A.C.`): conviene tomar la de la ficha cuando exista.

**Un lote en curso:** mientras se escribía esto ya se estaba ejecutando el lote de 400 (30 fichas con 0 verificaciones y 0 errores a las 07:39). Las cifras de arriba son de las 21 originales y se repetirán con el lote completo.

## 8. Siguientes pasos

1. **Lote de 400** (tú, ≈ 70 min). Con esas fichas se repite este análisis con una muestra real.
2. Decidir las propuestas **P1 y P5** (P4 ya está adoptada, D-22). Con el lote de 400 se ve cuántas empresas tienen cada padrón y cuántas quedan sin rubro.
3. Pendientes del spike: SP-08 (tabla CIIU oficial), SP-09 (política de privacidad de SUNAT) y la parte de Docker de SP-11.
4. Cerrar la puerta G1 con la muestra de 400: tasa de `PARSE_ERROR` (meta < 2 %) y de verificaciones (meta < 5 %). Con 21 fichas ya hay 0 % y 0 %.
