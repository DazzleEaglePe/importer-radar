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
| SP-06 | 20 consultas manuales de RUC | **Pendiente** | La haces tú (`docs/01` §9.1) |
| SP-07 | Frecuencia de verificación humana | **Pendiente** | Sale de SP-06 |
| SP-08 | Tabla CIIU oficial del INEI | **Pendiente** | — |
| SP-09 | Términos de las fuentes | **Parcial** | `robots.txt` revisados (`docs/01` §9.1). Falta leer la política de privacidad de SUNAT |
| SP-10 | Este informe | **En curso** | — |
| SP-11 | Huella en disco | **Parcial** | Lista: 5.5 MB. Padrón: 376 MB comprimido. Falta medir Docker y la base de datos |

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

## 6. Guía para las consultas manuales de RUC (SP-06)

**Para qué sirven estas 20 páginas:**
1. Ver **todos los campos** de la ficha completa, incluida la emisión electrónica que no se alcanzó a ver en la captura.
2. Armar los *fixtures* con los que se probará el parser (`docs/10` §6).
3. Medir **cuántas veces pide SUNAT una verificación humana** (SP-07).

**La lista:** `data/processed/aduanet/2026-10-25/sp06_muestra_20_ruc.csv` (fuera de git). Trae 18 empresas y 2 personas naturales, con la columna `para_probar`, el nombre de archivo sugerido y dos columnas vacías para tus anotaciones. Cubre S.A.C. (5), S.A. (4), E.I.R.L. (4), S.R.L. (2), una sucursal de empresa extranjera y otras dos formas; con y sin palabras clave; Lima, Callao y 7 departamentos de provincia. Se regenera con `scripts/spike/pick_sp06_sample.py` (semilla fija).

**Pasos, un RUC a la vez:**

1. Abre la consulta de SUNAT en tu Chrome: `https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp`.
2. En **Por RUC**, escribe el RUC de la lista y pulsa **Buscar**. Si SUNAT pide una verificación, resuélvela tú.
3. Cuando cargue la ficha, baja hasta el final y usa **Archivo → Guardar página como…** con el formato **«Página web, completa»**. Ponle de nombre el RUC y guárdala en `bot-scraping/data/raw/consulta_ruc/2026-10-25/`. («Solo HTML» podría guardar una página vacía si la ficha se arma con JavaScript.)
4. En la lista, anota en `pidio_verificacion` si fue **sí** o **no**, y en `observaciones` cualquier cosa rara.
5. Pulsa **Volver** y sigue con el siguiente.

**Reglas:**

- Consulta **uno por uno**, con el ritmo normal de quien lo hace a mano (unos 10 segundos entre consultas).
- Si aparece un bloqueo o un aviso de «demasiadas consultas», **detente**, anótalo y no insistas.
- Sin extensiones ni scripts de automatización: son consultas manuales a propósito.

**Qué hago yo:** no navego esa página (`docs/01` §9.1). Leo los archivos que guardes, extraigo los campos, comparo con `docs/05` §5 y armo los *fixtures*. Los de las personas naturales se vuelven sintéticos antes de entrar al repositorio, que es público (`docs/11` §10).

**Qué me dices al terminar:** cuántas veces pidió verificación, si algún RUC dio un error y si falta algún campo que esperabas ver.

## 7. Siguientes pasos

1. **Primer CSV (hito H1, versión provisional): generado.** Los 11,459 elegibles con razón social, tipo, estado, condición, departamento y prioridad, en `data/processed/aduanet/2026-10-25/importadores_activo_habido.csv` (fuera de git), hecho con `scripts/spike/export_h1_csv.py`. La prioridad va de 0 a 100: 7,095 empresas quedan en 70 (personas jurídicas en Lima o Callao sin palabra clave), 1,103 en 40 y 3,009 en 0 (casi todas personas naturales). **Solo 242 nombres (2.1 %) traen una palabra clave de electrónica**: el nombre ayuda a ordenar la cola, pero **no reemplaza la consulta del rubro (CIIU)**.
2. Tú haces las 20 consultas manuales (SP-06) y guardas cada página completa. Con eso cerramos SP-07 y calibramos la lectura de la ficha.
3. Leer la política de privacidad de SUNAT (SP-09) y medir la huella en disco (SP-11).
4. Cerrar este informe con la puerta G0, que ya se cumple en lo esencial: se llega a las dos fuentes masivas desde tu Mac.
