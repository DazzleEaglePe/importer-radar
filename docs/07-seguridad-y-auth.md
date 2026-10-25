# 07 · Seguridad y autenticación

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Alcance:** panel web, API, worker, base de datos, secretos y la conducta frente a las fuentes (SUNAT, Aduanet).
**Referencias de criterio:** OWASP ASVS y Cheat Sheets (contraseñas, sesiones, CSRF) y NIST SP 800-63B para el manejo de contraseñas.
**Aviso:** el apartado de datos personales (§7) describe buenas prácticas. **No es asesoría legal.** Revísalo con un abogado antes de abrir el acceso a más personas.

---

## 1. Principios

1. **Mínimo privilegio.** Cada rol puede hacer solo lo que necesita.
2. **El servidor decide.** Toda autorización se comprueba en la API, nunca solo en la interfaz.
3. **Todo lo que viene de fuera es dato no confiable.** Las páginas de SUNAT, los archivos subidos y las respuestas de terceros se validan y nunca se interpretan como código ni como HTML.
4. **Sin secretos en el código.** Ni en el repositorio, ni en los registros, ni en las imágenes.
5. **Cortesía con las fuentes.** Nada de evasión (§8).
6. **Rastro de lo sensible.** Quién hizo qué y cuándo.

## 2. Activos y modelo de amenazas

### 2.1 Qué protegemos

| Activo | Sensibilidad | Por qué importa |
| --- | --- | --- |
| Lista de proveedores, contactos y **cotizaciones** | **Alta** | Es tu ventaja comercial y contiene datos de contacto de personas |
| Datos de personas naturales (RUC `10…`) | **Media-alta** | Datos personales aunque provengan de una fuente pública |
| Cuentas de usuario y sesiones | **Alta** | Dan acceso a todo lo anterior |
| Claves de terceros (si se usan) y `SECRET_KEY` | **Crítica** | Permiten suplantar o gastar |
| Datos públicos de SUNAT (empresas) | Baja | Públicos. Su valor está en el cruce y la curación |
| Respaldo de la base de datos | **Alta** | Contiene todo |

### 2.2 Quién podría atacar

Un atacante externo que busca credenciales; un actor que explora el sitio por error de configuración; un usuario interno que se excede en permisos; contenido malicioso en archivos o páginas que el sistema procesa.

### 2.3 Amenazas principales y controles

| Amenaza | Ejemplo | Control |
| --- | --- | --- |
| **Robo de credenciales** | Fuerza bruta o contraseñas filtradas | Argon2id, bloqueo progresivo, límite por IP, contraseñas largas, 2FA opcional |
| **Secuestro de sesión** | Robo de cookie por XSS | Cookie `HttpOnly`, `Secure`, `SameSite=Lax`, sesiones en servidor, vencimiento |
| **CSRF** | Un sitio externo hace una acción con tu sesión | Token CSRF de doble envío + verificación de `Origin` |
| **XSS** | Razón social maliciosa en una página de SUNAT | Escape por defecto, **nunca** renderizar HTML crudo, CSP estricta |
| **Inyección SQL** | Parámetro `q` del listado | Consultas parametrizadas (SQLAlchemy). Sin SQL armado con texto del usuario |
| **Carga de archivos maliciosos** | ZIP bomba o ruta con `../` | Tipo y tamaño máximo, límites al descomprimir, nombres generados por el servidor |
| **SSRF** | Hacer que el servidor consulte una URL interna | Las URL de descarga salen **solo de la configuración**, nunca del usuario |
| **Elevación de privilegios** | Un `viewer` llama a un endpoint de administrador | Autorización por endpoint y prueba automatizada por cada ruta |
| **Fuga por registros** | Contraseñas o teléfonos en logs | Filtro de registros y prueba (RNF-OBS-02) |
| **Manipulación de datos en tránsito** | La lista de Aduanet viaja por HTTP | Validación de RUC con dígito verificador, contraste con el padrón y hash de cada archivo |
| **Pérdida de datos** | Disco dañado o borrado accidental | Respaldos cifrados diarios y prueba de restauración mensual |
| **Abuso de las fuentes** | El bot consulta sin parar y SUNAT bloquea la IP | Ritmo cortés, tope diario y pausa automática (§8) |

## 3. Autenticación

### 3.1 Alta de usuarios: solo por invitación

> **Hoy hay un único usuario.** El primer administrador se crea con `radar admin create`, que pide la contraseña por la terminal (nunca por argumentos ni archivos). El flujo de invitaciones se construye cuando se sume más gente (D-10).

1. El administrador crea una invitación (correo + rol). El sistema genera un **token aleatorio de 256 bits** y guarda solo su **SHA-256**.
2. El enlace de invitación vence a las **72 horas** y sirve **una sola vez**.
3. La persona abre el enlace, escribe su nombre y fija su contraseña. La invitación queda aceptada.
4. **No existe registro público.** Si no hay servidor de correo configurado, el administrador copia el enlace y lo envía por un canal seguro.

### 3.2 Inicio de sesión

- Método: **correo + contraseña**. Sin inicio con terceros en la primera versión.
- Respuesta de error **genérica** («Correo o contraseña incorrectos»), igual para correo inexistente y contraseña errónea, con **tiempo de respuesta equivalente** (se calcula un hash simulado cuando el correo no existe).
- **Bloqueo:** a los 5 intentos fallidos seguidos, la cuenta se bloquea 15 minutos. El contador se reinicia al iniciar sesión bien.
- **Límite por IP:** 5 inicios por minuto (`RATE_LIMITED`).
- Cada intento (bueno o malo) queda en la auditoría.

### 3.3 Contraseñas

| Regla | Valor |
| --- | --- |
| Algoritmo | **Argon2id**. Parámetros iniciales: memoria 64 MiB, 3 iteraciones, 1 hilo. Se ajustan para tardar unos 200 a 500 ms en el servidor real |
| Longitud mínima | **12 caracteres**. Se permiten frases largas y espacios. Sin reglas de «una mayúscula y un símbolo» |
| Máximo | 128 caracteres |
| Lista de contraseñas comunes | Se rechazan las de una lista local de las 10 000 más usadas y las que contienen el correo o el nombre |
| Rotación | **No** obligatoria por calendario. Solo si hay sospecha de filtración |
| Recuperación | En la primera versión, **restablecimiento por el administrador** (genera un enlace de un solo uso). Sin «olvidé mi contraseña» automático |
| Cambio | Exige la contraseña actual. Cierra las demás sesiones del usuario |

### 3.4 Sesiones

| Aspecto | Decisión |
| --- | --- |
| Identificador | Token aleatorio de 256 bits. En Redis se guarda **su hash**, no el valor |
| Cookie | Con HTTPS: `__Host-radar_session` con `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` y sin `Domain`. En `http://localhost` (modo local) se usa `radar_session` con `HttpOnly` y `SameSite=Lax`, porque Safari no acepta cookies `Secure` por HTTP. Lo controla `COOKIE_SECURE` |
| Vencimiento | **8 horas sin actividad** y **7 días como máximo** |
| Rotación | Se emite un identificador nuevo al iniciar sesión y al cambiar de rol o de contraseña |
| Revocación | Cerrar sesión la borra en Redis. El administrador puede cerrar todas las sesiones de un usuario al desactivarlo |
| Contenido | La sesión guarda solo el `user_id` y el rol vigente se consulta en cada solicitud |

### 3.5 Segundo factor (opcional, `Could`)

TOTP con códigos de recuperación, obligatorio para `admin` cuando se active. Está previsto en el modelo (`totp_secret_enc`) pero no en las primeras fases.

## 4. Autorización

| Acción | `viewer` | `analyst` | `admin` |
| --- | :---: | :---: | :---: |
| Ver embudo, listados, fichas, proveedores y cotizaciones | ✓ | ✓ | ✓ |
| **Exportar** CSV o XLSX | — | ✓ | ✓ |
| Forzar reconsulta, cargar ficha manual, pausar o reanudar la cola, cancelar tareas de consulta | — | ✓ | ✓ |
| Lanzar `ENQUEUE_LOOKUPS` y `SCORE` | — | ✓ | ✓ |
| Excluir o restaurar importadores | — | ✓ | ✓ |
| Crear y editar proveedores, eventos, cotizaciones y lista de verificación | — | ✓ | ✓ |
| Pasar un proveedor a `APPROVED` o `REJECTED` | — | ✓ | ✓ |
| Lanzar `INGEST_ADUANET` e `INGEST_PADRON`, subir archivos, cancelar ejecuciones | — | — | ✓ |
| Cambiar tope diario, ritmo y TTL de la cola | — | — | ✓ |
| Editar perfiles de puntuación y catálogo CIIU | — | — | ✓ |
| Gestionar usuarios, invitaciones y restablecer contraseñas | — | — | ✓ |
| Ver la auditoría | — | — | ✓ |

> Hoy solo existe `admin` (D-10). La matriz describe el diseño para cuando se sume más gente.

**Reglas adicionales**

- No se puede **quitar el rol de administrador al último administrador activo** ni desactivarlo.
- Un usuario no puede cambiar su propio rol.
- Cada ruta declara su rol mínimo en una dependencia de FastAPI. Una prueba recorre **todas** las rutas y falla si alguna no declara permiso.
- Los `viewer` no ven los datos de contacto personales de proveedores que son personas naturales (campo enmascarado).

## 5. Protección de la API y la web

| Control | Detalle |
| --- | --- |
| **HTTPS** | **Obligatorio si el panel se expone fuera de tu equipo**, con redirección y HSTS. En modo local el servidor escucha solo en `127.0.0.1` (`BIND_HOST`) y nada queda accesible desde tu red |
| **CSRF** | Cookie `__Host-radar_csrf` (`radar_csrf` en modo local) legible por la interfaz y cabecera `X-CSRF-Token` en toda solicitud que cambia datos. Además se verifica `Origin` y `Host` |
| **CORS** | **Sin CORS.** La interfaz y la API comparten origen detrás del proxy |
| **CSP** | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'` (los *nonces* se agregan si Next.js los exige) |
| **Otras cabeceras** | `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Permissions-Policy` restrictiva, `Cross-Origin-Opener-Policy: same-origin` |
| **Validación** | Pydantic en toda entrada. Longitudes máximas y listas de valores permitidos |
| **Salida** | La interfaz escapa todo por defecto. **Prohibido** `dangerouslySetInnerHTML` con datos de SUNAT o de usuarios |
| **Respuestas crudas** | Las guardadas en `/data/raw` **no se sirven** a la interfaz ni se abren en el navegador |
| **Subidas** | Solo `.zip`, `.txt`, `.csv`, `.html`. Tamaño máximo configurable. Se calcula el hash, se renombra el archivo y se limitan los bytes **descomprimidos** y el número de entradas del ZIP |
| **SQL** | Solo consultas parametrizadas. Los criterios de orden se validan contra una lista permitida |
| **Límites** | Tasa por usuario e IP. Tamaño máximo de cuerpo. Tiempo máximo por solicitud |
| **Errores** | Sin trazas ni detalles internos en las respuestas. El detalle va al registro con el `request_id` |

## 6. Secretos y configuración

| Secreto | Dónde vive | Cómo se rota |
| --- | --- | --- |
| `SECRET_KEY` | Variable de entorno del servidor | Cambiarla invalida sesiones y enlaces pendientes |
| Contraseña de PostgreSQL y Redis | Variables de entorno o *Docker secrets* | Cada 12 meses o ante sospecha |
| `THIRD_PARTY_API_KEY` (si existe) | Variable de entorno | Con el proveedor |
| Clave de cifrado de respaldos | Fuera del servidor (gestor de contraseñas) | Anual |

- El repositorio incluye `.env.example` **sin valores reales**. `.env` está en `.gitignore`.
- Un escáner de secretos corre en la integración continua y como *pre-commit*.
- **Clave SOL:** el sistema **no la pide, no la guarda y no la usa** (explicación en `docs/01` §9.2). Si SUNAT publica algún día un servicio oficial de consulta de RUC y quisieras usarlo, se haría con credenciales de una cuenta dedicada y los secretos vivirían solo en tu equipo. Eso requiere reabrir este documento.
- Las imágenes de Docker corren **sin root**, con sistema de archivos de solo lectura donde se pueda.

## 7. Datos personales

### 7.1 Qué datos personales hay

1. **Personas naturales con negocio** (RUC `10…`) en la lista de Aduanet y el padrón: nombre y domicilio fiscal. Son datos de una fuente pública, pero siguen siendo datos personales.
2. **Datos de contacto** que tus usuarios escriben a mano: nombre, cargo, teléfono, WhatsApp y correo de las personas con quienes tratan.
3. **Datos de los usuarios del panel**: nombre y correo.

### 7.2 Reglas

| Regla | Aplicación |
| --- | --- |
| **Finalidad limitada** | Solo para evaluar y gestionar proveedores. No se usan para mercadeo masivo ni se ceden a terceros (RNF-CUM-03) |
| **Minimización** | No se almacenan datos que no se necesitan. **No se extraen contactos** de redes sociales ni de páginas web |
| **Acceso restringido** | Solo usuarios autenticados. Los `viewer` ven los contactos de personas naturales enmascarados |
| **Sin exposición pública** | El panel no tiene páginas públicas con estos datos |
| **Registros sin datos personales** | Los logs no incluyen teléfonos, correos ni domicilios |
| **Conservación** | Contactos de proveedores rechazados: anonimización a los 24 meses. Auditoría: 12 meses |
| **Derechos de las personas** | Procedimiento interno para atender solicitudes de **acceso, rectificación, cancelación y oposición** (ARCO) en un máximo de 10 días hábiles: buscar a la persona, exportar o corregir, y suprimir o anonimizar. Queda registrado en la auditoría |
| **Respaldo** | Cifrado. La supresión se refleja en los respaldos al expirar la retención de 14 días |
| **Revisión legal** | Antes de compartir el panel con personas fuera de tu equipo, revisar la **Ley N.° 29733** y su reglamento vigente, y evaluar si hay que inscribir un banco de datos personales |

## 8. Conducta frente a las fuentes

Esta sección es una **línea roja del proyecto** (decisión D-06).

### 8.1 Lo que el sistema hace

- Usa **archivos de descarga oficial** (padrón reducido) para el trabajo en masa.
- Consulta el portal **un RUC a la vez**, con espera aleatoria de 6 a 12 s y tope diario.
- **Se detiene** ante verificación humana, 403 o 429, y avisa a una persona.
- Guarda la respuesta para **no repetir** consultas (caché de 30 días).
- Respeta los `robots.txt` de las fuentes y se revisan sus condiciones de uso antes de automatizar (D-18, `docs/01` §9.1).

### 8.2 Lo que el sistema NO hace

| Prohibido | Motivo |
| --- | --- |
| Resolver captchas de forma automática o con servicios de terceros | Es burlar un control de acceso |
| Rotar IP, usar *proxies* residenciales o cambiar de identidad para esquivar un bloqueo | Es evasión |
| Consultar en paralelo o a un ritmo que degrade el servicio | Daña un servicio público |
| Suplantar a un usuario o usar una Clave SOL ajena | Ilegítimo |
| Revender o publicar los datos de personas naturales | Vulnera la finalidad |

### 8.3 Si la fuente nos limita o nos escribe

1. Pausar la cola y **no reintentar** ese día.
2. Registrar el incidente en la auditoría.
3. Pasar a la **vía manual** (ficha cargada a mano) o a un proveedor alternativo con contrato.
4. Si SUNAT pide que se detenga el acceso, **se detiene**.

## 9. Infraestructura

| Control | Detalle |
| --- | --- |
| Exposición | **Modo local:** todo escucha en `127.0.0.1`. PostgreSQL y Redis **sin puertos públicos** (red interna de Docker). *Si algún día hay servidor:* solo los puertos 80 y 443 |
| Acceso al servidor | *Solo si algún día hay servidor:* SSH con llaves, sin contraseña, sin acceso de `root` y con cortafuegos activo |
| Actualizaciones | Actualizaciones de macOS activadas. Imágenes base y dependencias revisadas cada mes |
| Respaldos | `radar backup` (`pg_dump` **cifrado**) y una copia en un disco externo o una carpeta de nube cifrada. Retención de 7 copias. Prueba de restauración mensual |
| Monitoreo | Avisos dentro del panel: respaldo atrasado, cola pausada, error de parser y datos desactualizados |
| Entorno en tu equipo | Disco cifrado (FileVault) y bloqueo de pantalla, porque ahí vivirán los datos al inicio |

## 10. Auditoría

Eventos que **siempre** se registran: inicio de sesión (bueno y fallido), cierre de sesión, bloqueo de cuenta, invitación creada y aceptada, cambio de rol o de estado de un usuario, restablecimiento de contraseña, lanzamiento y cancelación de ejecuciones, cambios de la cola, carga de ficha manual, exclusión y restauración, aprobación o rechazo de proveedores, **exportaciones** (con sus filtros), cambios de perfiles y del catálogo CIIU, y solicitudes ARCO.

Cada registro guarda usuario, acción, entidad, datos relevantes, IP y agente de usuario. El registro **no se edita ni se borra** desde la aplicación. Retención de 12 meses.

## 11. Respuesta ante incidentes

| Paso | Qué hacer |
| --- | --- |
| 1. Contener | Cerrar todas las sesiones, desactivar al usuario afectado y rotar `SECRET_KEY` si hay sospecha de robo |
| 2. Evaluar | Revisar la auditoría y los registros del periodo. Determinar qué datos se vieron |
| 3. Recuperar | Restaurar desde respaldo si hubo alteración. Rotar credenciales y claves de terceros |
| 4. Informar | Avisar a las personas afectadas si hubo exposición de datos personales y evaluar las obligaciones legales (revisión legal) |
| 5. Aprender | Documentar la causa y agregar una prueba o un control para que no se repita |

## 12. Lista de comprobación antes de producción

- [ ] Si se expone fuera de tu equipo: HTTPS activo con HSTS y redirección desde HTTP. En modo local: comprobar que todo escucha solo en `127.0.0.1`.
- [ ] Cookies `__Host-…` con `HttpOnly`, `Secure` y `SameSite=Lax` verificadas.
- [ ] CSRF probado en todas las rutas que cambian datos.
- [ ] Una prueba confirma que **cada** ruta declara un rol mínimo.
- [ ] CSP activa sin `unsafe-inline` ni `unsafe-eval`.
- [ ] Sin `dangerouslySetInnerHTML` con datos externos.
- [ ] Límites de subida y de descompresión probados con un ZIP bomba.
- [ ] Escáner de secretos y auditoría de dependencias sin hallazgos altos o críticos.
- [ ] PostgreSQL y Redis sin puertos públicos.
- [ ] Respaldo cifrado probado con una restauración real.
- [ ] Un administrador de respaldo (otra persona de confianza) tiene acceso de emergencia.
- [ ] Términos de uso de las fuentes revisados.
- [ ] Revisión legal de datos personales hecha, si hay más personas que tú y tu equipo.
