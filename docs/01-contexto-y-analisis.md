# 01 · Contexto y análisis

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Fuente:** cuatro capturas de pantalla compartidas el 25/10/2026 (lista de Aduanet, formulario de Consulta RUC y resultado de una consulta), tus respuestas a las preguntas de arranque y a las preguntas abiertas, y una verificación rápida de las fuentes públicas de SUNAT. Lo que no sale de esas fuentes está marcado como *propuesto* o *por validar*.

---

## 1. Origen del proyecto

Vas a empezar a importar. El **primer lote será de teléfonos iPhone** y después vendrán laptops y dispositivos electrónicos en general. Para comprar con confianza necesitas **proveedores locales confiables**: empresas peruanas que ya importan, están formalmente activas y se dedican al rubro.

SUNAT ya publica dos cosas que sirven:

1. En **Aduanet**, la lista *«Relación de Importadores que han actualizado sus datos al 24/10/2026»*.
2. En su portal, la **Consulta RUC**, que muestra estado, condición, actividad económica y actividad de comercio exterior de cada contribuyente.

El trabajo es **automatizar el cruce** de ambas para no revisar la lista uno por uno.

## 2. Fuentes de datos

### 2.1 Lista de importadores (Aduanet)

| Aspecto | Lo que vimos |
| --- | --- |
| URL | `http://www.aduanet.gob.pe/servlet/CGListImp?flag=1&nom` (HTTP, sin cifrado: el navegador la marca «No seguro») |
| Título | *Actualización de datos del importador · R.M. 058-2001/EF* |
| Columnas | `RUC` · `IMPORTADOR` (razón social) · `ULT.ACT.` (fecha de última actualización, `dd/mm/aaaa`) |
| Orden | Alfabético por razón social: primero símbolos y comillas, luego números, luego letras |
| Estructura | Una sola tabla larga en una página. No vimos paginación ni filtros en la captura |
| Calidad | Razón social con comillas y espacios sobrantes (`" SERVICIOS GENERALES HUZA & OÑA E.I.R.L "`). **RUC repetidos**: `20526185847` aparece 4 veces (27/01/2014 y tres veces 24/01/2014). Mezcla de RUC `20…` (personas jurídicas) y `10…` (personas naturales con negocio) |
| Tamaño | **Desconocido.** Hay que medirlo en el spike |
| Acceso | Desde el entorno de desarrollo el servidor **rechazó la conexión** (`ECONNREFUSED`). **Desde tu Mac sí respondió** (prueba del 25/10/2026 sobre otra página del mismo servidor). Falta bajar la lista completa para medir su tamaño |

**Corrección importante al planteamiento inicial:** esta lista **no es «los importadores más grandes del Perú»**. Es la relación de quienes *actualizaron sus datos* como importadores, ordenada alfabéticamente. No trae volumen, montos ni productos. Sirve como **universo de empresas registradas como importadoras**, no como ranking.

### 2.2 Padrón reducido del RUC (descarga masiva)

SUNAT ofrece el [padrón reducido del RUC](https://orientacion.sunat.gob.pe/padron-reducido-del-ruc-para-descarga) para descarga. Según la página oficial, incluye: **RUC, razón social, estado del contribuyente, condición de domicilio, ubigeo y dirección fiscal**, más una segunda lista con los anexos (otros locales) de cada RUC.

- Un repositorio comunitario lo describe con **más de 11 millones de registros**. Es una cifra aproximada de terceros, no oficial.
- **No trae actividad económica (CIIU).** Por eso no reemplaza a la consulta puntual.
- El formato exacto del archivo, su codificación y su frecuencia de actualización **se confirman al descargarlo** (spike). Históricamente ha sido un ZIP con un TXT delimitado por `|`.
- Con 11 millones de filas, **no se carga entero a la base de datos**: se procesa en streaming y solo se guardan las filas cuyo RUC está en nuestra lista de importadores.

### 2.3 Consulta RUC individual (portal SUNAT)

El formulario permite buscar *Por RUC*, *Por Documento* y *Por Nomb./Raz.Soc.*. Para un RUC, el resultado de tu captura muestra:

| Campo | Ejemplo (RUC `20526185847`) |
| --- | --- |
| Número de RUC y razón social | `20526185847 - " SERVICIOS GENERALES HUZA & OÑA E.I.R.L "` |
| Tipo de contribuyente | Empresa individual de resp. ltda. |
| Fecha de inscripción / inicio de actividades | 20/08/2010 |
| **Estado del contribuyente** | **BAJA DE OFICIO** · fecha de baja 31/10/2024 |
| **Condición del contribuyente** | **HABIDO** |
| Domicilio fiscal | Piura (no se reproduce aquí) |
| Sistema de emisión de comprobante | Manual |
| **Actividad de comercio exterior** | **IMPORTADOR/EXPORTADOR** |
| Sistema de contabilidad | Manual/computarizado |
| **Actividades económicas** | Principal `4923` transporte de carga por carretera · Secundaria 1 `7730` alquiler de maquinaria · Secundaria 2 `4663` venta al por mayor de materiales de construcción |
| Comprobantes autorizados | Factura, boleta de venta (la lista sigue más abajo) |

Lecciones de este ejemplo:

- **Estado y condición son campos independientes.** Esta empresa está de baja y a la vez es HABIDO. Hay que filtrar por **ambos**.
- Aparecer en la lista de importadores **no significa estar vigente**.
- El **CIIU (Rev. 4)** es lo que permite saber si la empresa vende electrónica. Los códigos relevantes se detallan en la sección 6.

> **Verificación anti-bot:** esta consulta puede pedir una verificación humana (captcha) según el momento y el volumen. El sistema **no la evade**. Ver decisión D-06.

### 2.4 Otras vías de consulta (evaluadas)

| Vía | Qué ofrece | Pro | Contra |
| --- | --- | --- | --- |
| Padrón reducido + consulta puntual (**elegida**) | Estado/condición en masa; CIIU solo de finalistas | Oficial, gratis, mínima presión sobre SUNAT | La consulta puntual es lenta y puede pedir verificación humana |
| API de un tercero de pago | JSON limpio por RUC | Rápida, estable | Costo recurrente, depende de un tercero |
| API oficial de SUNAT | OAuth con credenciales de Clave SOL | Oficial | Los manuales encontrados cubren comprobantes de pago y estados financieros. **No se confirmó un servicio de consulta de RUC.** Requiere Clave SOL |

La arquitectura deja la fuente de consulta **intercambiable** (ver `docs/04`), así que cambiar de vía más adelante no obliga a rehacer nada.

## 3. Problema actual (as-is)

1. La lista de SUNAT tiene miles de filas (por medir), sin buscador ni filtros útiles.
2. Para saber si una empresa sirve hay que abrir su consulta RUC una por una y leerla.
3. La lista tiene duplicados y empresas dadas de baja.
4. Nada indica qué empresas se dedican a la electrónica.

## 4. Propuesta (to-be)

Un panel web interno con un **pipeline automático** y una **vista de revisión**:

- El pipeline carga la lista, filtra en masa, consulta por prioridad y puntúa.
- El panel muestra el embudo, deja filtrar y ordenar, explica cada puntaje y permite armar la lista de proveedores con contactos, cotizaciones y verificación.
- Una **línea de comandos** (`radar`) ejecuta lo mismo sin interfaz. Sirve para el primer CSV rápido y para automatizar.

## 5. Decisiones tomadas

| ID | Decisión | Origen |
| --- | --- | --- |
| D-01 | Las empresas son **proveedores locales** a quienes comprarles. No son solo referencia ni agentes de importación | Tu respuesta 25/10 |
| D-02 | Herramienta **interna** para ti y tu equipo, con login. Sin registro público | Tu respuesta 25/10 |
| D-03 | Fuente de RUC: **padrón reducido** (estado y condición en masa) + **consulta puntual** (CIIU y comercio exterior de finalistas) | Tu respuesta 25/10 |
| D-04 | Stack: **Python + FastAPI + Playwright**, **Next.js**, **PostgreSQL** y **Redis** para colas | Tu respuesta 25/10 |
| D-05 | Primer perfil de búsqueda: **smartphones / iPhone**. Alcance posterior: laptops y electrónicos en general | Tu mensaje |
| D-06 | **No se evaden captchas ni bloqueos.** Si SUNAT pide verificación humana, la cola se pausa y la tarea pasa a manual | Política del proyecto |
| D-07 | El puntaje es una **señal pública explicable**, nunca un sello de confianza. La verificación final es humana | Propuesto |
| D-08 | Un hito **sin interfaz** (CSV filtrado) va primero, porque el primer lote de iPhone no puede esperar al panel | Propuesto |
| D-09 | Los usuarios entran por **invitación del administrador**. Roles: administrador, analista, lector | Propuesto, mismo criterio que PaseLibre |
| D-10 | **Un solo usuario (administrador)** por ahora. Los roles `analyst` y `viewer` y las invitaciones quedan diseñados, pero se construyen cuando se sume más gente | Tu respuesta 25/10 |
| D-11 | Todo corre **en tu Mac**, sin VPS. El panel escucha solo en `127.0.0.1` | Tu respuesta 25/10 |
| D-12 | **Sin Clave SOL, sin API oficial y sin servicios de pago.** No hay presupuesto para datos. Solo se construyen los proveedores `sunat_web` y `manual` | Tu respuesta 25/10 |
| D-13 | `ACTIVO` y `HABIDO` son **obligatorios**. Lo ideal son 5 años o más de antigüedad. Con menos de 5 años **no se descarta**, pero el nivel no pasa de B. No hay tope máximo de antigüedad | Tu respuesta 25/10 (interpretación por confirmar, §9.3) |
| D-14 | Se registran **todos los estados del equipo**: nuevo sellado, reacondicionado y usado. El objetivo es reunir mucha información para decidir después | Tu respuesta 25/10 |
| D-15 | Los avisos se muestran **solo dentro del panel**. Sin correo ni WhatsApp | Tu respuesta 25/10 |
| D-16 | Categorías: **iPhone primero**, después laptops Apple, accesorios y cargadores, repuestos y baterías. Cuatro perfiles de partida | Tu respuesta 25/10 |
| D-17 | El nombre **Radar de Importadores** queda confirmado | Tu respuesta 25/10 |
| D-18 | Los términos de las fuentes se revisan en lo posible (§9.1). Las consultas manuales del spike las haces **tú**, no yo, porque el `robots.txt` de la consulta RUC bloquea a los agentes de Anthropic | Revisión del 25/10 |

## 6. Cómo se decide qué es «confiable» (propuesto)

Se separa en **filtros eliminatorios** (si fallan, la empresa se descarta del todo) y **puntaje** (ordena lo que queda). Los pesos viven en un perfil configurable (ver `docs/02` y `docs/05`).

**Filtros eliminatorios**

1. Estado = `ACTIVO`.
2. Condición = `HABIDO`.
3. Actividad de comercio exterior incluye `IMPORTADOR`.
4. No excluida manualmente.

**Puntaje (perfil «Smartphones / iPhone v1», total 100)**

| Criterio | Máx. | Cómo se calcula |
| --- | --- | --- |
| Rubro (CIIU) | 40 | Peso del mejor código relevante. La actividad principal cuenta completa; una secundaria, al 80 % |
| Antigüedad | 20 | Años desde la inscripción: menos de 1 → 0 · 1 a 3 → 8 · 3 a 5 → 14 · 5 o más → 20 |
| Forma societaria | 10 | S.A., S.A.C., S.R.L. → 10 · E.I.R.L. → 6 · persona natural → 3 |
| Formalidad de comprobantes | 10 | Autorizada a emitir factura → 5 · emisor electrónico → 5 |
| Actualización en Aduanet | 10 | Última actualización de hasta 2 años → 10 · hasta 5 → 5 · más antigua → 0 |
| Cercanía logística | 10 | Domicilio fiscal en Lima o Callao (ubigeo `15` o `07`) → 10 |

**Niveles:** A ≥ 75 · B 55–74 · C 35–54 · D < 35.

**Tope por antigüedad (D-13):** una empresa con menos de 5 años de inscrita **no se descarta**, pero su nivel no puede pasar de B, aunque su puntaje sea alto. No hay tope máximo: una empresa de 30 años cuenta igual que una de 5, siempre que sea `ACTIVO` y `HABIDO`.

> **`ACTIVO` y `HABIDO` no son lo mismo.** `ACTIVO` es el *estado* del contribuyente (no está de baja ni suspendido). `HABIDO` es la *condición* del domicilio (SUNAT pudo ubicarlo). Una empresa puede ser HABIDA y estar dada de baja, como la de tu captura. Por eso se exigen **las dos**.

**Códigos CIIU Rev. 4 de partida** (a validar contra la tabla oficial del INEI antes del lanzamiento):

| Código | Descripción orientativa | Peso |
| --- | --- | --- |
| `4652` | Venta al por mayor de equipo, partes y piezas electrónicos y de telecomunicaciones | 1.0 |
| `4651` | Venta al por mayor de computadoras, equipo periférico y programas informáticos | 1.0 |
| `4741` | Venta al por menor de computadoras, periféricos, programas y equipo de telecomunicaciones en comercios especializados | 0.6 |
| `4742` | Venta al por menor de equipo de sonido y video en comercios especializados | 0.3 |
| `4659` | Venta al por mayor de otros tipos de maquinaria y equipo | 0.2 |

> Las descripciones de los códigos salen de la estructura general de la CIIU Rev. 4 y de fuentes colombianas (DIAN). No las tomamos como texto oficial peruano hasta contrastarlas con el INEI.

> **Dato por confirmar:** el criterio «emisor electrónico → 5» depende de un campo que **no se ve en tus capturas** (la consulta se corta en «Comprobantes de pago»). Si la página completa no lo trae con claridad, ese medio criterio se reasigna en la versión 2 del perfil.

### 6.1 Perfiles de partida (D-16)

Cada categoría tiene su propio perfil, con los mismos criterios pero distinto peso por código CIIU. Los pesos son una **propuesta inicial** que se calibra en el spike con los códigos que realmente aparezcan en los importadores.

| Perfil (`key`) | Para qué | Códigos CIIU y pesos de partida |
| --- | --- | --- |
| `smartphones` | iPhone nuevos, reacondicionados y usados | 4652 → 1.0 · 4651 → 1.0 · 4741 → 0.6 · 4742 → 0.3 · 4659 → 0.2 |
| `laptops` | Laptops (incluidas Apple) y computadoras | 4651 → 1.0 · 4652 → 0.8 · 4741 → 0.6 · 4659 → 0.2 |
| `accessories` | Accesorios y cargadores | 4652 → 1.0 · 4651 → 0.6 · 4741 → 0.5 · 4742 → 0.3 · 4659 → 0.3 |
| `parts` | Repuestos y baterías | 4652 → 1.0 · 4659 → 0.4 · 9511 → 0.3 · 9512 → 0.3 |

`9511` y `9512` corresponden a la reparación de computadoras y de equipo de comunicaciones (por validar con la tabla del INEI). Una empresa que repara equipos suele **comprar** repuestos más que venderlos al por mayor, por eso pesan poco. Todos los perfiles comparten los filtros eliminatorios.

## 7. Qué NO cubre este proyecto

- Verificar que un proveedor venda producto **original**, nuevo o con garantía Apple. Es verificación humana (lista de verificación en `docs/08`).
- Saber el **volumen** que importa cada empresa. SUNAT no lo publica por empresa. Los proveedores de datos de comercio exterior sí, pero son de pago. Queda como mejora futura vía importación de CSV (RF-ING-07). La partida arancelaria de teléfonos inteligentes es la `8517.13` en el sistema armonizado vigente; **confírmalo con tu agente de aduanas**.
- Contactar, negociar, pagar o comprar. El sistema solo prepara y registra.
- Consultas con Clave SOL (deudas, declaraciones, etc.).

## 8. Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación |
| --- | --- | --- | --- | --- |
| R-01 | Aduanet o SUNAT rechazan o limitan las conexiones automáticas | Media (rechazó la conexión desde el entorno de prueba, pero respondió desde tu Mac) | Alto | Todo corre en tu Mac. Ingesta por **archivo cargado a mano** como alternativa |
| R-02 | La consulta RUC pide captcha o limita el volumen | Alta | Alto | Prefiltro en masa con el padrón, cola priorizada, ritmo bajo, pausa automática y **fallback manual**. Opción de proveedor de pago intercambiable |
| R-03 | Cambia el HTML de SUNAT y el parser devuelve datos erróneos | Media | Alto | Parsers con pruebas sobre HTML guardado, validación estricta y alerta. Un parseo que falla **no guarda datos basura** |
| R-04 | Se interpreta el puntaje como garantía y se compra a un estafador | Media | Muy alto | Mensajes claros en la interfaz, lista de verificación obligatoria antes de «Aprobar», y no usar el nombre «confiable» como sello |
| R-05 | Datos personales de personas naturales (RUC `10…`) mal tratados | Media | Medio | Uso interno, sin exposición pública, accesos con roles y registro de auditoría (`docs/07`) |
| R-06 | El volumen de la lista es mayor al esperado y la consulta puntual tarda semanas | Media | Medio | Priorización por señales baratas, parar cuando haya suficientes nivel A, y posibilidad de proveedor de pago |
| R-07 | La lista de Aduanet viaja por HTTP y podría alterarse en tránsito | Baja | Medio | Validar RUC con dígito verificador, contrastar con el padrón y registrar hash de cada archivo |
| R-08 | Cambian los términos de uso de las fuentes | Baja | Medio | Revisar condiciones antes de automatizar y mantener el uso en volúmenes bajos |

## 9. Preguntas abiertas y respuestas

Respondidas el 25/10/2026:

| # | Pregunta | Tu respuesta | Decisión |
| --- | --- | --- | --- |
| 1 | Equipo | Solo tú, como administrador, por ahora | D-10 |
| 2 | Dónde corre | En tu Mac, sin VPS | D-11 |
| 3 | Clave SOL | Preguntaste para qué serviría. Explicación en §9.2 | D-12 |
| 4 | Presupuesto para datos | Ninguno | D-12 |
| 5 | Criterios de confianza | 5 años o más como ideal, sin excluir a los más antiguos, siempre `ACTIVO` y `HABIDO` | D-13 |
| 6 | Condiciones del equipo | Todas: nuevo, reacondicionado y usado. Reunir mucha información para decidir | D-14 |
| 7 | Avisos | Dentro del panel | D-15 |
| 8 | Otras categorías | Sí: laptops Apple, accesorios y cargadores, repuestos y baterías | D-16 |
| 9 | Nombre | «Radar de Importadores» | D-17 |
| 10 | Términos de las fuentes | Pediste una explicación. Revisión en §9.1 | D-18 |

### 9.1 Términos de las fuentes: qué son y qué se revisó

**Qué son.** Los *términos de uso* son las reglas que una entidad pone para usar su página web y sus datos: por ejemplo, si permite consultas automáticas, cuántas por minuto, si se puede reutilizar la información o si prohíbe copiarla en masa. Importan por tres razones: (1) si las incumples pueden bloquear tu IP o tu cuenta, (2) pueden limitar qué haces con los datos y (3) los datos de personas naturales tienen reglas propias de privacidad (`docs/07` §7). No es un trámite: es leer las reglas del sitio antes de automatizar contra él.

**Qué se revisó el 25/10/2026:**

| Fuente | Resultado |
| --- | --- |
| `www.sunat.gob.pe/robots.txt` | No existe (404) |
| `www.aduanet.gob.pe/robots.txt` | No existe: el servidor devuelve su página genérica |
| `e-consultaruc.sunat.gob.pe/robots.txt` | Existe y lo administra Cloudflare. Permite el acceso general (`Allow: /`) y declara **`ai-train=no`** (no usar el contenido para entrenar IA). **Bloquea por nombre** a rastreadores de IA como `ClaudeBot` y `GPTBot` |
| Página principal de SUNAT | **No tiene un enlace de términos de uso ni de aviso legal.** Solo publica una Política de Privacidad y el procedimiento para ejercer los derechos ARCO |
| Búsqueda de términos sobre acceso automatizado o reutilización | **No encontré un texto oficial** |

**Qué significa para el proyecto:**

- Tu herramienta es **tu propio programa**, no un rastreador de IA. Consulta pocos RUC, con pausas, para uso interno y sin entrenar nada. Encaja con lo que el sitio permite en su `robots.txt`.
- El sitio usa Cloudflare, que puede mostrar verificaciones anti-bot. Eso encaja con el riesgo R-02 y con la regla de **no evadirlas**.
- Como el `robots.txt` bloquea a los agentes de Anthropic, **yo no navego esa página por ti**. Las consultas manuales del spike las haces tú en tu navegador y me pasas las páginas guardadas para analizarlas.
- Queda pendiente leer la Política de Privacidad de SUNAT y el procedimiento ARCO (tarea SP-09) y ver si Aduanet publica sus propias condiciones.
- Este análisis **no es asesoría legal**. Si el proyecto crece o se abre a más personas, conviene una revisión formal.

### 9.2 ¿Para qué sirve la Clave SOL y por qué no la necesitamos?

La **Clave SOL** es el usuario y la contraseña con los que una empresa o persona entra a *SUNAT Operaciones en Línea*: ahí presenta declaraciones, emite comprobantes, ve su deuda y hace trámites. Es **privada y da poder sobre la vida tributaria** de quien la tiene.

**Por qué podría aparecer en este proyecto:** SUNAT ofrece APIs oficiales y sus credenciales se generan **desde SOL**. Los manuales que encontré cubren comprobantes de pago y estados financieros. **No confirmé** un servicio oficial de consulta de RUC.

**Por qué no la usamos:**

1. La Consulta RUC pública y el padrón **no la piden**.
2. Un programa automático con tu Clave SOL expone tu cuenta tributaria, y SUNAT puede bloquearla si detecta un uso anómalo.
3. No hace falta para saber si una empresa ajena está activa y qué actividad tiene.

**Decisión:** no se pide, no se guarda y no se usa (D-12). Solo se reabriría si SUNAT publica un servicio oficial de consulta de RUC y quisieras usarlo, con una cuenta dedicada.

### 9.3 Todavía abiertas

| # | Tema | Mi propuesta | Efecto |
| --- | --- | --- | --- |
| a | **Antigüedad.** Entendí «mínimo 5 años, sin excluir a los más antiguos» como: 5 años o más es lo ideal, y con menos **no se descarta** pero el nivel no pasa de B | Dejarlo así. Si prefieres que la menor antigüedad **sí descarte**, se cambia a un filtro eliminatorio | `docs/05` §6.1 |
| b | **Respaldos.** Dónde guardar la copia cifrada de la base de datos: disco externo o una carpeta de nube (OneDrive) cifrada | Tú eliges. Con la nube, siempre cifrada | `docs/03`, `docs/07` §9 |
| c | **Pesos de los perfiles nuevos.** Los de laptops, accesorios y repuestos son una propuesta | Calibrarlos en el spike con los códigos CIIU reales | `docs/01` §6.1 |

## 10. Glosario

| Término | Significado |
| --- | --- |
| **RUC** | Registro Único de Contribuyentes. 11 dígitos. Prefijo `20` = persona jurídica, `10` = persona natural con negocio |
| **Estado** | Situación del contribuyente: `ACTIVO`, suspensión temporal, baja provisional, baja definitiva, baja de oficio, baja provisional por oficio. Valores exactos por confirmar en el padrón |
| **Condición** | Si SUNAT pudo verificar el domicilio fiscal: `HABIDO`, `NO HABIDO`, `NO HALLADO`, `PENDIENTE`. Valores exactos por confirmar |
| **CIIU** | Clasificación Industrial Internacional Uniforme (Rev. 4). Código de 4 dígitos de la actividad económica |
| **Padrón reducido** | Archivo de descarga masiva de SUNAT con datos básicos de los RUC |
| **Aduanet** | Portal de la aduana de SUNAT donde está la lista de importadores |
| **Ubigeo** | Código de ubicación geográfica del INEI. Lima = `15`, Callao = `07` (primeros dos dígitos) |
| **Nivel (tier)** | A, B, C o D según el puntaje de un perfil |
| **Perfil de puntuación** | Conjunto de pesos y códigos CIIU para un tipo de producto (iPhone, laptops…) |
| **Spike** | Prueba corta para eliminar una duda técnica antes de construir |
