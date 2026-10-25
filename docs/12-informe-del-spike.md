# 12 · Informe del spike (semana 1)

**Versión:** 0.1 (en curso) · **Fecha:** 25/10/2026
**Qué es:** el registro de lo que se midió y se probó en el spike (`docs/10` §4), con cifras reales. Se actualiza a medida que se cierran las tareas.
**Datos:** los archivos originales viven en `data/` (fuera de git). Aquí solo hay cifras y formato, sin nombres de personas.

---

## 1. Estado de las tareas

| # | Tarea | Estado | Resultado |
| --- | --- | --- | --- |
| SP-01 | Contar las filas de la lista de Aduanet | **Pendiente** | Hace falta que guardes la página desde tu navegador (§2.3) |
| SP-02 | Descarga automática de la lista | **Hecha: no funciona por acceso directo** | Cuatro solicitudes dieron 404 o error de red (§2.1) |
| SP-03 | Formato del padrón reducido | **Hecha** | §3 |
| SP-04 | Valores de estado y condición | **Hecha** | §3.4 |
| SP-05 | Cruce lista × padrón (tamaño real del embudo) | **Pendiente** | Necesita la lista de Aduanet |
| SP-06 | 20 consultas manuales de RUC | **Pendiente** | La haces tú (`docs/01` §9.1) |
| SP-07 | Frecuencia de verificación humana | **Pendiente** | Sale de SP-06 |
| SP-08 | Tabla CIIU oficial del INEI | **Pendiente** | — |
| SP-09 | Términos de las fuentes | **Parcial** | `robots.txt` revisados (`docs/01` §9.1). Falta leer la política de privacidad de SUNAT |
| SP-10 | Este informe | **En curso** | — |
| SP-11 | Huella en disco | **Parcial** | Padrón medido (§3.1). Falta medir Docker y la base de datos |

## 2. Lista de importadores de Aduanet

### 2.1 Lo que se probó

Todas las solicitudes fueron `GET` simples a la dirección de tu captura, sin cambiar cabeceras para parecer otro cliente.

| # | Cliente | Dirección | Resultado |
| --- | --- | --- | --- |
| 1 | `curl` con identificación propia | `http://www.aduanet.gob.pe/servlet/CGListImp?flag=1&nom` | **404** (1,214 bytes, «Error 404--Not Found») |
| 2 | `curl` con identificación propia | `http://aduanet.gob.pe/servlet/CGListImp?flag=1&nom` | **404** (2,002 bytes) |
| 3 | Chrome (ventana nueva, sin sesión previa) | La misma, sin `www` | **Error de red** |
| 4 | Chrome (ventana nueva, sin sesión previa) | La misma, con `www` | **404** (título «Error 404--Not Found») |

Las pruebas 1 y 2 devuelven un 404 de servidor de aplicaciones. La 4 confirma que no es un problema del cliente.

### 2.2 Qué significa

- El servidor **responde**, pero la lista **no se entrega por acceso directo a esa dirección**. Tu pestaña la cargó porque llegaste por otro camino.
- Posibles causas, **sin confirmar**: hace falta una cookie de sesión, una página de referencia (haber hecho clic desde otra sección del portal) o un paso previo de navegación.
- No se probó cambiar cabeceras, identificarse como un navegador ni reproducir cookies: sería esquivar un control de acceso (`docs/07` §8).
- **Consecuencia para el diseño:** la **carga de la lista desde un archivo guardado por ti pasa a ser la vía principal**, y la descarga automática queda como mejora futura si se entiende el flujo de navegación. El riesgo R-01 sube de «Media» a «Alta» para la descarga automática, pero **no frena el proyecto**: el archivo guardado ya estaba previsto (RF-ING-01).

### 2.3 Qué falta (tarea tuya, 2 minutos)

1. En la pestaña de Chrome donde tienes la lista abierta: **Archivo → Guardar página como…**, formato **«Página web, solo HTML»**.
2. Guárdala en `bot-scraping/data/raw/aduanet/2026-10-25/lista.html`.
3. Dime **cómo llegaste a esa página** (desde qué sección del portal de Aduanet o de SUNAT y con qué clics). Eso se documenta y puede servir para automatizarlo de forma legítima más adelante.

Con el archivo mido filas, RUC únicos, duplicados, RUC inválidos, la proporción `10` / `20`, y cruzo con el padrón (SP-05).

## 3. Padrón reducido del RUC

### 3.1 El archivo

| Aspecto | Valor medido el 25/10/2026 |
| --- | --- |
| Página oficial | `https://www.sunat.gob.pe/descargaPRR/mrc137_padron_reducido.html`, que dice «Actualizado al 25/10/2026» |
| Enlace del archivo | `http://www2.sunat.gob.pe/padron_reducido_ruc.zip` |
| Tamaño del ZIP | **394,170,330 bytes (376 MiB)**. Coincide con el `Content-Length` anunciado |
| Última modificación | 25/10/2026 08:36 GMT. Es del mismo día de la página, así que **parece diario** (se confirma observando varios días) |
| Descarga | 52.6 s a unos 7.5 MB/s |
| Contenido | **1 solo archivo:** `padron_reducido_ruc.txt`, **1,578,572,502 bytes (1.47 GiB)** descomprimido. Se lee en streaming, sin descomprimir a disco |
| Archivo anexo (locales) | `padron_reducido_local_anexo.zip`, 14,068,105 bytes. No se usa por ahora |
| Procesamiento | Leer las **18,486,442 filas** en streaming y contar valores tomó **26 s**. La memoria no se midió, pero no se cargó nada en RAM salvo contadores |

### 3.2 Formato

| Aspecto | Valor |
| --- | --- |
| Codificación | **No es UTF-8**: el 6.0 % de las líneas (1,117,169) no son UTF-8 válido. Se decodifica como **ISO-8859-1 / `latin-1`** (por verificar con nombres con Ñ y tildes) |
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
| Filas **sin ubigeo** (`-`) | 15,760,371 (85.3 %). Coincide con el peso de los RUC `10`: parece que **a las personas naturales no se les publica el domicilio** (por confirmar) |
| Filas con ubigeo de 6 dígitos | 2,726,066 |

### 3.4 Valores de estado y condición

**Los valores vienen truncados a 20 caracteres.** Por eso aparecen cosas como `BAJA PROV. POR OFICI` o `NO HALLADO SE MUDO D`. El filtro compara con los valores exactos `ACTIVO` y `HABIDO`, que no se truncan.

**Estado del contribuyente** (todas las filas):

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

**Condición de domicilio** (todas las filas):

| Valor | Filas |
| --- | ---: |
| `HABIDO` | 16,815,687 |
| `NO HABIDO` | 756,900 |
| `NO APLICABLE` | 581,121 |
| `-` | 87,898 |
| `NO HALLADO …` (9 variantes: `SE MUDO D`, `DESTINATA`, `CERRADO`, `OTROS MOT`, `RECHAZADO`, `NRO.PUERT`, `NO EXISTE`, `FALLECIO` y `NO HALLADO` solo) | 197,239 en total |
| `PENDIENTE` | 25,268 |
| `POR VERIFICAR` | 2,344 |

**Combinaciones en RUC `20`** (personas jurídicas), las más frecuentes:

| Estado | Condición | Filas | % de los RUC `20` |
| --- | --- | ---: | ---: |
| `BAJA DE OFICIO` | `HABIDO` | 911,749 | 38.5 % |
| **`ACTIVO`** | **`HABIDO`** | **871,239** | **36.8 %** |
| `BAJA DE OFICIO` | `NO HABIDO` | 290,962 | 12.3 % |
| `SUSPENSION TEMPORAL` | `HABIDO` | 63,546 | 2.7 % |
| `ACTIVO` | `NO HABIDO` | 15,259 | 0.6 % |

Dos lecturas útiles:

- **Más de 6 de cada 10 personas jurídicas del padrón están de baja o suspendidas.** Aparecer en una lista no dice nada de la vigencia, como ya se veía en tu primer ejemplo.
- La combinación `BAJA DE OFICIO` + `HABIDO` es **más frecuente** que `ACTIVO` + `HABIDO`. Por eso el filtro por estado es indispensable y filtrar solo por condición dejaría pasar casi la mitad de basura.

## 4. Ajustes a los documentos que salen de este spike

| Documento | Ajuste |
| --- | --- |
| `docs/01` §2.1, §2.2, §8 (R-01), glosario | Acceso a Aduanet, formato real del padrón, valores truncados |
| `docs/03` §1 | Volumen del padrón (18.5 M) y proporción ACTIVO + HABIDO medida |
| `docs/04` §5.4, §6.3 | Lectura del padrón (codificación, delimitador, normalización, cuarentena) y `PADRON_URL` |
| `docs/05` §4 | Normalización de `estado`, `condicion` y `ubigeo` |
| `docs/10` §4 | Estado de cada tarea del spike |

## 5. Siguientes pasos

1. Guardar la lista de Aduanet (§2.3) y contarme cómo llegaste a ella.
2. Con la lista: SP-01 y SP-05 (tamaño real del embudo). El padrón hay que bajarlo de nuevo para el cruce (1 minuto, 376 MB) y se vuelve a mover a la Papelera.
3. Tú haces las 20 consultas manuales (SP-06) y guardas cada página completa.
4. Cerrar el informe con las decisiones para la puerta G0.
