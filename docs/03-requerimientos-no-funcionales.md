# 03 · Requerimientos no funcionales

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Fuente:** `docs/01-contexto-y-analisis.md` y `docs/02-requerimientos-funcionales.md`.
**Cómo leerlo:** cada requerimiento tiene una **meta medible** y una forma de **comprobarla**. Las metas son *propuestas* y se recalibran después del spike de la semana 1, cuando se conozca el tamaño real de los datos.

---

## 1. Supuestos de volumen

| Dato | Supuesto | Estado |
| --- | --- | --- |
| Filas en la lista de Aduanet | **26,297** | Medido el 25/10/2026 |
| RUC únicos tras deduplicar | **26,003** (98.9 % de las filas) | Medido |
| Registros del padrón reducido | **18,486,442** | Medido el 25/10/2026 |
| Importadores ACTIVO + HABIDO | **11,459** (44.1 % de los RUC únicos): 8,440 personas jurídicas, 2,924 naturales y 95 de otros prefijos | Medido |
| Usuarios del panel | 1 (tú) | Confirmado |
| Usuarios simultáneos | 1 | Derivado |
| Consultas RUC por día | 300 a 500 | Propuesto (ritmo cortés) |

**Consecuencia del volumen:** a 6 a 12 segundos por consulta se hacen unas 300 a 600 por hora de trabajo continuo, pero el tope diario de 400 es el límite real. Consultar los 11,459 elegibles llevaría **unos 29 días** (unos 21 si solo se consultan las personas jurídicas). Por eso el diseño es: filtrar en masa, **priorizar** y **parar cuando ya hay suficientes nivel A**, no consultar todo.

## 2. Rendimiento

| ID | Requerimiento | Meta | Cómo se comprueba |
| --- | --- | --- | --- |
| RNF-REN-01 | Listado de importadores con filtros y orden (50 000 filas en base) | p95 ≤ 400 ms en el servidor | Prueba de carga con datos sintéticos |
| RNF-REN-02 | Búsqueda por razón social con tolerancia a errores | p95 ≤ 500 ms | Índice trigram y prueba con 100 búsquedas |
| RNF-REN-03 | Ingesta de la lista de Aduanet | ≤ 5 min para 100 000 filas, sin contar la descarga | Cronometrar con archivo de prueba |
| RNF-REN-04 | Procesar el padrón reducido (18.5 M de filas) | ≤ 15 min y **memoria ≤ 512 MB** | **Medido: 26 s** para leer las 18.5 M de filas en streaming. Falta medir la memoria máxima |
| RNF-REN-05 | Recalcular puntajes de 50 000 importadores | ≤ 60 s | Prueba automatizada |
| RNF-REN-06 | Carga inicial del panel | LCP ≤ 2.5 s en red doméstica | Lighthouse |
| RNF-REN-07 | Exportar 50 000 filas a CSV | ≤ 20 s, en flujo continuo (sin cargar todo en memoria) | Prueba automatizada |

## 3. Cortesía con las fuentes

SUNAT es una entidad pública y sus servicios no son infinitos. El sistema debe comportarse como **un visitante paciente**.

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-COR-01 | Concurrencia hacia SUNAT | **1 solicitud a la vez**, nunca en paralelo |
| RNF-COR-02 | Espera entre consultas | Aleatoria entre 6 y 12 s (configurable) |
| RNF-COR-03 | Tope diario | 400 consultas por defecto. Cambiarlo requiere rol `admin` y queda auditado |
| RNF-COR-04 | Reintentos | Máximo 3, con espera creciente (1, 5 y 15 min). Después, `FAILED` |
| RNF-COR-05 | Respuestas 403, 429 o verificación humana | **Pausa automática de la cola** y aviso. Sin reintentos agresivos |
| RNF-COR-06 | Descargas masivas (padrón, lista) | Máximo una por fuente y por día, salvo orden manual del administrador |
| RNF-COR-07 | Horario | Las ejecuciones programadas corren de madrugada hora de Lima (America/Lima) |
| RNF-COR-08 | Prohibiciones | Sin resolución automática de captchas, sin rotación de IP o proxies para esquivar bloqueos, sin suplantar identidades. Ver `docs/07` §8 |

## 4. Fiabilidad y continuidad

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-FIA-01 | Disponibilidad del panel | Disponible mientras tu Mac y Docker estén encendidos. Sin objetivo de 24/7 (D-11) |
| RNF-FIA-02 | Procesos **reanudables**: si se corta la luz o se reinicia el servidor, la cola y las ingestas continúan donde quedaron | Estado en la base de datos, no en memoria |
| RNF-FIA-03 | Procesos **idempotentes**: repetir una ingesta o un puntaje produce el mismo resultado sin duplicar | Claves únicas y pruebas |
| RNF-FIA-04 | Respaldo de la base de datos | Comando `radar backup` (cifrado) que se puede programar, con retención de 7 copias y una copia en un disco externo o una carpeta de nube **cifrada** (`docs/01` §9.3 b) |
| RNF-FIA-05 | Objetivos de recuperación | RPO ≤ 24 h · RTO ≤ 4 h |
| RNF-FIA-06 | Prueba de restauración | Una vez al mes se restaura un respaldo en un entorno de prueba |
| RNF-FIA-07 | Un fallo del scraper **no tumba** el panel ni la API | Procesos separados |

## 5. Integridad y trazabilidad de datos

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-DAT-01 | Cada dato de SUNAT guarda **fuente y fecha de obtención** | 100 % de los campos de la ficha |
| RNF-DAT-02 | Los archivos originales y las respuestas crudas se conservan | Padrón: **solo el último archivo**, porque el espacio de tu Mac importa (`PADRON_KEEP_FILES`, por defecto 1) · Lista de Aduanet: todas las versiones (pesan poco) · Respuestas de consulta: sin vencimiento mientras el volumen sea pequeño |
| RNF-DAT-03 | Un parseo defectuoso **nunca** sobrescribe datos buenos | Validación de campos obligatorios antes de guardar |
| RNF-DAT-04 | Frescura | Estado y condición del padrón: reverificación semanal · Ficha de consulta puntual: 30 días de caché |
| RNF-DAT-05 | Los cambios de estado y condición dejan historial | Tabla de historial, sin borrado |
| RNF-DAT-06 | Los puntajes son **reproducibles**: guardan la versión del perfil y el desglose | Verificable con una prueba que recalcula y compara |

## 6. Seguridad y privacidad

El detalle está en `docs/07`. Aquí solo las metas.

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-SEG-01 | El panel solo escucha en `127.0.0.1`. **Si algún día se expone fuera de tu equipo, HTTPS es obligatorio** | TLS 1.2 o superior y HSTS cuando se exponga |
| RNF-SEG-02 | Contraseñas con **Argon2id** | Parámetros mínimos de OWASP o superiores |
| RNF-SEG-03 | Sesión en cookie `HttpOnly` y `SameSite=Lax` siempre. `Secure` y el prefijo `__Host-` cuando hay HTTPS (en `localhost` van sin ellos) | Verificado con prueba automatizada |
| RNF-SEG-04 | Acceso a datos por rol, comprobado **en el servidor** | Prueba por cada endpoint |
| RNF-SEG-05 | Sin secretos en el repositorio ni en los registros | Escáner de secretos en la integración continua |
| RNF-SEG-06 | Dependencias sin vulnerabilidades conocidas **altas o críticas** | Auditoría en cada integración |
| RNF-SEG-07 | Datos personales de personas naturales **solo visibles para usuarios autenticados** y sin exposición pública | Revisión manual de rutas |
| RNF-SEG-08 | Auditoría de acciones sensibles | Conservada 12 meses |

## 7. Usabilidad y accesibilidad

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-USA-01 | Idioma de la interfaz | Español del Perú (`es-PE`) |
| RNF-USA-02 | Zona horaria y formato | `America/Lima`, fechas `dd/mm/aaaa`, números con punto decimal y coma de miles, moneda `S/` y `US$` |
| RNF-USA-03 | Accesibilidad | **WCAG 2.1 AA**: contraste, teclado completo, foco visible, etiquetas |
| RNF-USA-04 | Estados por color **siempre acompañados de texto o ícono** | Revisión de componentes |
| RNF-USA-05 | Pantalla principal usable en **escritorio y tablet**. En celular solo lectura cómoda | Pruebas en 3 anchos |
| RNF-USA-06 | Un analista nuevo llega de la lista a «agregar proveedor» sin ayuda | Prueba con una persona, ≤ 5 min |
| RNF-USA-07 | Mensajes de error con **qué pasó y qué hacer** | Revisión de textos |
| RNF-USA-08 | Navegadores | Chrome, Edge, Safari y Firefox en sus dos últimas versiones mayores |

## 8. Mantenibilidad y calidad

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-MAN-01 | Cobertura de pruebas del **backend** | ≥ 80 % en módulos de ingesta, puntaje y autenticación |
| RNF-MAN-02 | Los **parsers** se prueban con **HTML guardado** (fixtures), nunca contra SUNAT en vivo | 100 % de los parsers |
| RNF-MAN-03 | Tipado estático | `mypy` estricto en el backend y TypeScript `strict` en el frontend |
| RNF-MAN-04 | Formato y análisis estático automáticos | `ruff`, `eslint` y `prettier` en la integración continua |
| RNF-MAN-05 | Migraciones de base de datos versionadas | Alembic, sin cambios manuales |
| RNF-MAN-06 | **Contrato de API generado** (OpenAPI) y cliente tipado del frontend generado desde él | Sin tipos duplicados a mano |
| RNF-MAN-07 | Documentación viva | Cada decisión de arquitectura nueva se agrega a `docs/04` |
| RNF-MAN-08 | Un módulo de fuente (proveedor de consulta) se agrega **sin tocar** el resto | Interfaz común y prueba de contrato |

## 9. Observabilidad

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-OBS-01 | Registros **estructurados (JSON)** con identificador de solicitud y de ejecución | Todos los servicios |
| RNF-OBS-02 | Los registros **no contienen** contraseñas, tokens ni datos de contacto | Prueba de filtrado |
| RNF-OBS-03 | Métricas: consultas hechas, fallidas, `NEEDS_HUMAN`, duración, profundidad de cola | Endpoint `/metrics` (Prometheus) |
| RNF-OBS-04 | Avisos: cola pausada, parser roto, respaldo atrasado, datos desactualizados | **Dentro del panel** (RF-OPS-05) |
| RNF-OBS-05 | Chequeos de salud | `/health` (vivo) y `/ready` (base de datos y Redis) |

## 10. Portabilidad y despliegue

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-POR-01 | Todo corre con **Docker Compose** en desarrollo y producción | Un comando levanta el entorno |
| RNF-POR-02 | Configuración por **variables de entorno** | Sin valores fijos en el código |
| RNF-POR-03 | Actualización repetible del entorno local | `make up` reconstruye todo, con imágenes versionadas y vuelta a la versión anterior. Un despliegue en servidor queda fuera de alcance (D-11) |
| RNF-POR-04 | Arranque en un equipo nuevo | ≤ 30 min siguiendo el README |

## 11. Costos

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-COS-01 | Infraestructura | **US$ 0**: todo corre en tu Mac (D-11) |
| RNF-COS-02 | Servicios de terceros de pago | **Ninguno.** No hay presupuesto para datos (D-12) |
| RNF-COS-03 | Licencias | Solo software libre o gratuito |
| RNF-COS-04 | **Huella en disco** en tu Mac | ≤ 5 GB en total (imágenes de Docker, base de datos y archivos). **Meta a medir en el spike** (SP-11). Si se pasa, el worker corre fuera de Docker |

## 12. Cumplimiento

| ID | Requerimiento | Meta |
| --- | --- | --- |
| RNF-CUM-01 | Tratamiento de datos personales conforme a la **Ley N.° 29733** y su reglamento vigente | Revisión con asesoría legal antes de abrir el acceso a más personas |
| RNF-CUM-02 | Respeto de los **`robots.txt` y los términos de uso** de Aduanet y SUNAT | Revisión previa a la automatización (D-18, `docs/01` §9.1) |
| RNF-CUM-03 | Finalidad limitada: los datos se usan solo para evaluar proveedores | Sin cesión a terceros |

## 13. Resumen de prioridades

| Prioridad | Requerimientos |
| --- | --- |
| **Imprescindibles desde H1** | RNF-COR-01 a 05, RNF-FIA-02, RNF-FIA-03, RNF-DAT-01, RNF-DAT-03, RNF-REN-03, RNF-REN-04, RNF-MAN-02 |
| **Antes de abrir el panel (H3)** | RNF-SEG-01 a 05, RNF-USA-01 a 04, RNF-REN-01, RNF-REN-02, RNF-OBS-01 |
| **Antes de producción (H5)** | RNF-FIA-04 a 06, RNF-SEG-06 a 08, RNF-OBS-03 a 05, RNF-POR-03, RNF-CUM-01 y 02 |
