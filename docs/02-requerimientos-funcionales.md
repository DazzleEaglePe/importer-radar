# 02 · Requerimientos funcionales

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Fuente:** `docs/01-contexto-y-analisis.md`.
**Prioridad (MoSCoW):** **M** = debe estar · **S** = debería · **C** = podría · **W** = no en esta etapa.
**Fase:** la entrega en la que se construye (ver `docs/10`). **H1** = CSV sin interfaz · **H2** = consulta y puntaje · **H3** = panel · **H4** = proveedores · **H5** = endurecimiento.

---

## 1. Actores

| Actor | Qué hace | Rol en el sistema |
| --- | --- | --- |
| **Administrador** | Configura, invita usuarios, lanza y cancela procesos, edita perfiles | `admin` |
| **Analista de compras** | Explora importadores, gestiona proveedores, lanza consultas | `analyst` |
| **Lector** | Mira el embudo, la lista y las fichas sin modificar nada | `viewer` |
| **Sistema (worker)** | Ejecuta ingestas, cola de consultas, puntajes y tareas programadas | proceso interno |

> Hoy el único usuario eres tú, como `admin` (D-10). Los otros roles son diseño para cuando se sume más gente.

## 2. Resumen del flujo principal

```
Cargar lista Aduanet → Cruzar con padrón → Cola de consultas RUC → Puntaje → Revisar → Proveedor → Verificar → Aprobar
```

## 3. Requerimientos

### 3.1 Ingesta (ING)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-ING-01 | Importar la lista de Aduanet, ya sea descargándola de su URL o **cargando un archivo guardado** (HTML o CSV). Extraer RUC, razón social y fecha de última actualización | M | H1 |
| RF-ING-02 | Normalizar la razón social (mayúsculas, sin comillas ni espacios sobrantes, sin tildes para búsqueda) y **conservar el texto original** | M | H1 |
| RF-ING-03 | **Deduplicar por RUC**: quedarse con la fecha de última actualización más reciente y contar cuántas veces aparece | M | H1 |
| RF-ING-04 | Validar cada RUC: 11 dígitos, prefijo válido (`10`, `15`, `16`, `17`, `20`) y **dígito verificador (módulo 11)**. Las filas inválidas van a una lista de cuarentena con el motivo, no se descartan en silencio | M | H1 |
| RF-ING-05 | Registrar cada ingesta como **snapshot**: fuente, fecha declarada por la fuente, fecha de descarga, hash del archivo, total de filas, filas nuevas e inválidas. Si el hash ya existe, avisar y no reprocesar | M | H1 |
| RF-ING-06 | Importar el **padrón reducido** (descarga o archivo) en **streaming**, guardando solo las filas cuyo RUC está en nuestra lista. Conservar estado, condición, ubigeo y dirección fiscal | M | H1 |
| RF-ING-07 | Importar un **CSV externo** (por ejemplo, datos de comercio exterior de un proveedor de pago) con RUC y columnas opcionales (volumen, partidas) para enriquecer la ficha | C | Posterior |
| RF-ING-08 | Detectar y registrar **cambios de estado o condición** entre snapshots del padrón en un historial | S | H2 |
| RF-ING-09 | **Reingesta** manual desde el panel o la línea de comandos, y programada (semanal) mientras el worker esté encendido. Si los datos tienen más de 14 días, el panel lo avisa | S | H5 |

### 3.2 Filtrado en masa (FIL)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-FIL-01 | Descartar automáticamente, con **motivo registrado**, a toda empresa cuyo estado no sea `ACTIVO` (`ESTADO_NO_ACTIVO`) o cuya condición no sea `HABIDO` (`CONDICION_NO_HABIDO`) | M | H1 |
| RF-FIL-02 | Mostrar el **embudo** con conteos por etapa y por motivo de descarte | M | H1 (CLI), H3 (panel) |
| RF-FIL-03 | **Priorizar** la cola de consultas con señales baratas: RUC `20`, Lima/Callao, actualización reciente en Aduanet y palabras clave en la razón social (por ejemplo `TECH`, `CELULAR`, `TELECOM`, `COMPUTER`, `DIGITAL`, `ELECTRON`, `MOBILE`). Las palabras clave **suben prioridad, nunca excluyen** | S | H2 |
| RF-FIL-04 | Los umbrales y las listas de palabras son **configurables** sin tocar código | S | H2 |

### 3.3 Consulta RUC (CON)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-CON-01 | **Cola de consultas** con estados `QUEUED`, `RUNNING`, `DONE`, `FAILED`, `NEEDS_HUMAN`, `CANCELLED`, con historial de intentos y errores | M | H2 |
| RF-CON-02 | Consultar un RUC en SUNAT y extraer: razón social, tipo de contribuyente, nombre comercial, fecha de inscripción y de inicio de actividades, estado y fecha de baja, condición, domicilio fiscal, sistema de emisión, **actividad de comercio exterior**, sistema de contabilidad, **actividades económicas (principal y secundarias con CIIU)** y comprobantes autorizados | M | H2 |
| RF-CON-03 | **Ritmo cortés y configurable**: una consulta a la vez, pausa aleatoria entre consultas (por defecto 6 a 12 segundos), tope diario (por defecto 400), reintentos con espera creciente y límite de intentos | M | H2 |
| RF-CON-04 | Si aparece **verificación humana** (captcha) o bloqueo repetido (403/429), **no evadirlo**: la tarea pasa a `NEEDS_HUMAN`, la cola se **pausa automáticamente** y se muestra un aviso en el panel | M | H2 |
| RF-CON-05 | **Ingreso manual de la ficha**: formulario o pegado de texto de la consulta oficial para resolver tareas `NEEDS_HUMAN`. Queda marcada como fuente `MANUAL` y con el usuario que la cargó | M | H2 |
| RF-CON-06 | El origen de la consulta es **intercambiable** (portal SUNAT, API de un tercero, API oficial, manual) sin cambiar el resto del sistema. Por ahora solo se construyen `sunat_web` y `manual` (D-12) | S | H2 |
| RF-CON-07 | **Caché**: no reconsultar un RUC antes de 30 días (configurable), salvo reconsulta forzada por un usuario | M | H2 |
| RF-CON-08 | Guardar la **respuesta cruda** de cada consulta para auditar y reprocesar si cambia el parser | M | H2 |
| RF-CON-09 | **Detectar cambios de formato**: si faltan campos obligatorios, la consulta falla de forma controlada, **no guarda datos parciales como válidos** y genera una alerta | M | H2 |
| RF-CON-10 | Poder **pausar, reanudar y vaciar** la cola, y cambiar la prioridad de un RUC | S | H3 |
| RF-CON-11 | **Modo asistido** (solo si el worker corre en tu equipo): el navegador se abre visible para que **una persona** resuelva la verificación y el proceso continúe. No automatiza la resolución | C | H2 |

### 3.4 Puntaje (PUN)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-PUN-01 | **Catálogo CIIU** editable: código, descripción, categoría de relevancia (`ELECTRONICS_CORE`, `ELECTRONICS_RETAIL`, `ELECTRONICS_RELATED`, `NONE`) y peso | M | H2 |
| RF-PUN-02 | **Perfiles de puntuación versionados**. Se entregan cuatro de partida (`docs/01` §6.1): `smartphones` (iPhone), `laptops` (incluidas Apple), `accessories` (accesorios y cargadores) y `parts` (repuestos y baterías). Solo uno activo por tipo de producto | M | H2 |
| RF-PUN-03 | Calcular **puntaje (0–100) y nivel (A–D)** con **desglose por criterio**, para poder explicar cada número | M | H2 |
| RF-PUN-04 | **Recalcular** al cambiar un perfil o el catálogo CIIU **sin volver a consultar SUNAT** | M | H2 |
| RF-PUN-05 | Mostrar por qué una empresa es A y otra B (comparación de desgloses) | C | Posterior |
| RF-PUN-06 | **Tope de nivel por antigüedad**: una empresa con menos de 5 años de inscrita no se descarta, pero no puede pasar de nivel B. El umbral y el nivel máximo son configurables en el perfil, y el desglose muestra cuándo se aplicó el tope | M | H2 |

### 3.5 Explorar importadores (IMP)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-IMP-01 | **Listado paginado** con búsqueda por RUC y razón social (**tolerante a tildes y errores de tipeo**) y filtros por etapa, estado, condición, nivel, perfil, CIIU, departamento, tipo de RUC y comercio exterior | M | H3 |
| RF-IMP-02 | **Ficha del importador**: datos de SUNAT con la fecha y la fuente de cada dato, actividades, historial de estado, puntaje desglosado, tareas de consulta y enlace a la consulta oficial | M | H3 |
| RF-IMP-03 | **Ordenar** por puntaje, antigüedad, última actualización y nombre | M | H3 |
| RF-IMP-04 | **Exportar a CSV y XLSX** la vista filtrada | M | H1 (CSV por CLI), H3 |
| RF-IMP-05 | **Forzar reconsulta** de un RUC desde la ficha | S | H3 |
| RF-IMP-06 | **Excluir manualmente** a una empresa con motivo (lista negra interna) y poder revertirlo | S | H3 |
| RF-IMP-07 | **Vistas guardadas** de filtros (por ejemplo «iPhone · nivel A · Lima») | C | Posterior |

### 3.6 Proveedores (PRO)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-PRO-01 | **Agregar un importador a Proveedores** desde el listado o la ficha. Un RUC es proveedor una sola vez | M | H4 |
| RF-PRO-02 | Estados de seguimiento: `CANDIDATE` → `CONTACTED` → `QUOTED` → `VERIFYING` → `APPROVED` o `REJECTED`. Cada cambio queda en la línea de tiempo | M | H4 |
| RF-PRO-03 | **Datos de contacto** escritos a mano: persona, cargo, teléfono, WhatsApp, correo, web y dirección. El sistema **no los extrae ni los adivina** | M | H4 |
| RF-PRO-04 | **Línea de tiempo** de eventos: notas, llamadas, mensajes, visitas y cotizaciones, con autor y fecha | M | H4 |
| RF-PRO-05 | **Cotizaciones** por producto: categoría, modelo, capacidad, condición (nuevo sellado, reacondicionado o usado), **grado** y **salud de batería** (usados y reacondicionados), precio unitario, moneda (USD o PEN), cantidad mínima, vigencia, si incluye IGV, **garantía**, **plazo de entrega** y **stock**. El objetivo es reunir mucha información para decidir (D-14) | M | H4 |
| RF-PRO-06 | **Lista de verificación** configurable (valores de partida en `docs/08`). **No se puede pasar a `APPROVED` con puntos obligatorios sin marcar** | M | H4 |
| RF-PRO-07 | **Aviso dentro del panel** cuando un proveedor aprobado o en verificación cambia de estado o condición en SUNAT (D-15). El sistema no cambia el estado del proveedor por su cuenta | S | H5 |
| RF-PRO-08 | **Comparar cotizaciones** entre proveedores para un mismo producto | S | H4 |
| RF-PRO-09 | Exportar la lista de proveedores a CSV y XLSX | S | H4 |
| RF-PRO-10 | **Categorías por proveedor** (`smartphones`, `laptops`, `accessories`, `parts`…): un proveedor puede tener varias y la lista se filtra por categoría | M | H4 |

### 3.7 Acceso y administración (AUT)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-AUT-01 | Iniciar y cerrar sesión con correo y contraseña. Cambiar la contraseña propia | M | H3 |
| RF-AUT-02 | **Invitación** del administrador por enlace de un solo uso con vencimiento. **No hay registro público**. Se construye cuando se sume más gente (D-10) | S | Posterior |
| RF-AUT-03 | Roles `admin`, `analyst` y `viewer` con permisos según `docs/07`. En la primera versión existe un único `admin`; el modelo ya incluye los otros dos | S | Posterior |
| RF-AUT-04 | El administrador puede **desactivar** usuarios y restablecer contraseñas | S | Posterior |
| RF-AUT-05 | **Registro de auditoría** de acciones sensibles (inicios de sesión, cambios de rol, lanzar y cancelar procesos, exclusiones, aprobaciones, exportaciones) | M | H3 |
| RF-AUT-06 | Segundo factor con TOTP | C | Posterior |
| RF-AUT-07 | Crear el **primer administrador por línea de comandos** (`radar admin create`), pidiendo la contraseña por la terminal | M | H3 |

### 3.8 Operación (OPS)

| ID | Requerimiento | P | Fase |
| --- | --- | --- | --- |
| RF-OPS-01 | **Dashboard con el embudo**: total de RUC únicos → activos y habidos → consultados → con rubro relevante → nivel A/B → proveedores | M | H3 |
| RF-OPS-02 | **Panel de ejecuciones**: tipo, estado, inicio, duración, conteos y errores. Poder cancelar una ejecución | M | H3 |
| RF-OPS-03 | **Línea de comandos `radar`** con los mismos procesos (ingestar, filtrar, encolar, puntuar, exportar), sin necesidad de la interfaz | M | H1 |
| RF-OPS-04 | Estado de la cola visible: pendientes, en curso, hechas hoy, tope diario, motivo de pausa | M | H3 |
| RF-OPS-05 | **Avisos dentro del panel** (campana y banners): cola pausada, parser roto, proveedor cambió de estado, datos desactualizados, respaldo atrasado. Cada aviso se cierra solo cuando la causa desaparece, o lo descarta el usuario. Sin correo ni WhatsApp (D-15) | M | H3 |

## 4. Fuera de alcance (W)

- Verificar autenticidad de productos o distribuidores autorizados de Apple de forma automática.
- Enviar mensajes, correos o llamadas a proveedores en automático.
- Evadir captchas, rotar proxies para esquivar bloqueos o usar servicios de resolución de captcha.
- Compras, pagos, cartas fianza o cualquier transacción.
- Consultas protegidas por Clave SOL (deudas, declaraciones).
- Scraping de redes sociales, marketplaces o páginas de las empresas para sacar contactos.
- Registro público de usuarios o acceso de terceros.
- Avisos por correo o WhatsApp (D-15).
- Servicios de pago, API de terceros y API oficial de SUNAT por ahora (D-12).
- Despliegue en un servidor o VPS (D-11).

## 5. Criterios de aceptación clave

Los casos usan datos reales de tus capturas como material de prueba (solo RUC, estado y CIIU).

**AC-01 · Deduplicación (RF-ING-03)**
- *Dado* que la lista trae cuatro filas del RUC `20526185847` con fechas 27/01/2014, 24/01/2014, 24/01/2014 y 24/01/2014,
- *Cuando* se ingesta,
- *Entonces* existe **un solo** importador con `aduanet_last_update = 2014-01-27` y `aduanet_appearances = 4`.

**AC-02 · Validación de RUC (RF-ING-04)**
- *Dado* un archivo con `20526185847` y `20526185848` (dígito verificador alterado),
- *Entonces* el primero entra y el segundo va a cuarentena con motivo `DIGITO_VERIFICADOR_INVALIDO`.

**AC-03 · Normalización (RF-ING-02)**
- *Dado* `" SERVICIOS GENERALES HUZA & OÑA E.I.R.L "` (con comillas y espacios),
- *Entonces* `razon_social` queda `SERVICIOS GENERALES HUZA & OÑA E.I.R.L`, y `razon_social_norm` queda sin tildes ni comillas para la búsqueda. El texto original se conserva en el snapshot.

**AC-04 · Descarte por estado (RF-FIL-01)**
- *Dado* que el RUC `20526185847` tiene estado `BAJA DE OFICIO` y condición `HABIDO`,
- *Entonces* queda en etapa `DISCARDED` con motivo `ESTADO_NO_ACTIVO`. Aunque sea HABIDO, **no avanza** a la cola de consultas.

**AC-05 · Verificación humana (RF-CON-04)**
- *Dado* que SUNAT responde con un desafío de verificación en la consulta de un RUC,
- *Entonces* la tarea pasa a `NEEDS_HUMAN`, la cola queda **pausada** con motivo `HUMAN_VERIFICATION`, no se hace ningún intento de resolverlo y el panel muestra el aviso con un botón «Cargar ficha a mano».

**AC-06 · Extracción de actividades (RF-CON-02)**
- *Dado* el HTML guardado de la consulta del RUC `20526185847`,
- *Entonces* se extraen tres actividades: `4923` principal, `7730` secundaria 1 y `4663` secundaria 2, además de `IMPORTADOR/EXPORTADOR` como actividad de comercio exterior y fecha de baja `2024-10-31`.

**AC-07 · Parser roto (RF-CON-09)**
- *Dado* un HTML al que le falta la tabla de actividades económicas,
- *Entonces* la consulta queda `FAILED` con motivo `PARSE_ERROR`, **no se actualiza** la ficha existente y se genera una alerta.

**AC-08 · Puntaje explicable (RF-PUN-03)**
- *Dado* un importador activo y habido con actividad principal `4652`, inscrito hace 7 años, S.A.C., autorizado a facturar y con emisión electrónica, domicilio en Lima y actualización en Aduanet de hace 1 año,
- *Entonces* el puntaje es **40 + 20 + 10 + 10 + 10 + 10 = 100**, nivel A, y el desglose muestra cada línea.

**AC-09 · Recalcular sin consultar (RF-PUN-04)**
- *Dado* un cambio de peso del código `4741` de 0.6 a 0.8,
- *Cuando* se recalcula,
- *Entonces* cambian los puntajes afectados y **no se crea ninguna tarea de consulta** a SUNAT.

**AC-10 · Aprobación con verificación (RF-PRO-06)**
- *Dado* un proveedor en `VERIFYING` con un punto obligatorio sin marcar,
- *Cuando* un analista intenta pasarlo a `APPROVED`,
- *Entonces* el sistema lo impide y lista los puntos pendientes.

**AC-11 · Permisos (RF-AUT-03, cuando existan más usuarios)**
- *Dado* un usuario `viewer`,
- *Cuando* intenta lanzar una ingesta o editar un proveedor,
- *Entonces* recibe un error de permisos y queda registrado en la auditoría.

**AC-12 · Tope por antigüedad (RF-PUN-06)**
- *Dado* un importador `ACTIVO` y `HABIDO` con 3 años de inscrito, actividad principal `4652`, S.A.C., facturación electrónica, domicilio en Lima y actualización en Aduanet de hace 1 año (puntaje **94**: 40 + 14 + 10 + 10 + 10 + 10),
- *Entonces* su nivel es **B** y no A. El puntaje sigue siendo 94 y el desglose muestra `tier_cap` con la regla aplicada.
