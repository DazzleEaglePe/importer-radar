# 06 · API contract

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Base:** `/api/v1` · **Formato:** JSON (`application/json`) · **Especificación viva:** FastAPI publica el OpenAPI 3.1 en `/api/v1/openapi.json`. El frontend genera su cliente tipado desde ese archivo. **Este documento define el contrato esperado; si el generado difiere, se corrige uno de los dos.**

---

## 1. Convenciones

| Tema | Regla |
| --- | --- |
| Nombres | Campos en `snake_case`. Los del dominio SUNAT en español (`razon_social`, `estado`) |
| Fechas | `date`: `2026-10-24`. Instantes: ISO 8601 en UTC (`2026-10-25T14:03:00Z`). La interfaz los muestra en `America/Lima` |
| Identificadores | Importadores por `ruc` (texto de 11 dígitos). Resto por número o UUID |
| Paginación | `?page=1&page_size=50` (máximo 200). Respuesta `{ "items": [...], "page": 1, "page_size": 50, "total": 1234 }` |
| Orden | `?sort=-score,razon_social` (el `-` indica descendente). Cada recurso lista los campos permitidos |
| Autenticación | Cookie de sesión `__Host-radar_session` (HttpOnly). En modo local se llama `radar_session` (`docs/07` §3.4) |
| CSRF | Toda solicitud que cambia datos (`POST`, `PUT`, `PATCH`, `DELETE`) envía `X-CSRF-Token` con el valor de la cookie `__Host-radar_csrf` (`radar_csrf` en modo local) |
| Trabajos largos | Responden `202 Accepted` con `{ "run_id": 42 }` y `Location: /api/v1/pipeline/runs/42`. Se consulta por sondeo cada 5 s |
| Trazabilidad | Cada respuesta incluye `X-Request-ID` |
| Reintentos seguros | `Idempotency-Key` opcional en `POST /pipeline/runs` |
| Límites | Inicio de sesión: 5 por minuto por IP. General: 120 por minuto por usuario. Respuesta `429` con `Retry-After` |

### 1.1 Errores (RFC 9457)

`Content-Type: application/problem+json`

```json
{
  "type": "https://radar.local/errors/forbidden",
  "title": "No tienes permiso para esta acción",
  "status": 403,
  "code": "FORBIDDEN",
  "detail": "Tu rol (viewer) no puede lanzar ingestas.",
  "request_id": "01JBX7…",
  "errors": []
}
```

Para validaciones, `errors` lista los campos: `[{ "field": "email", "message": "Correo no válido" }]`.

| `code` | HTTP | Cuándo |
| --- | --- | --- |
| `UNAUTHENTICATED` | 401 | Sin sesión o sesión vencida |
| `FORBIDDEN` | 403 | El rol no permite la acción |
| `CSRF_INVALID` | 403 | Falta o no coincide el token |
| `NOT_FOUND` | 404 | El recurso no existe |
| `VALIDATION_ERROR` | 422 | Datos mal formados |
| `CONFLICT` | 409 | Estado incompatible (por ejemplo, proveedor ya existente) |
| `CHECKLIST_INCOMPLETE` | 409 | Aprobar proveedor con puntos obligatorios sin marcar |
| `ALREADY_PROCESSED` | 409 | Archivo con hash ya procesado |
| `RATE_LIMITED` | 429 | Demasiadas solicitudes |
| `INTERNAL_ERROR` | 500 | Error no previsto (sin detalles internos) |

## 2. Enumeraciones

| Nombre | Valores |
| --- | --- |
| `Role` | `admin`, `analyst`, `viewer` |
| `Stage` | `INGESTED`, `PADRON_CHECKED`, `QUEUED`, `LOOKED_UP`, `SCORED`, `DISCARDED` |
| `DiscardReason` | `ESTADO_NO_ACTIVO`, `CONDICION_NO_HABIDO`, `NO_ENCONTRADO_EN_PADRON`, `SIN_ACTIVIDAD_IMPORTADOR`, `EXCLUIDO_MANUAL` |
| `Tier` | `A`, `B`, `C`, `D` |
| `LookupStatus` | `QUEUED`, `RUNNING`, `DONE`, `FAILED`, `NEEDS_HUMAN`, `CANCELLED` |
| `RunKind` | `INGEST_ADUANET`, `INGEST_PADRON`, `ENQUEUE_LOOKUPS`, `SCORE`, `REFRESH_STATUS` |
| `RunStatus` | `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED` |
| `SupplierStatus` | `CANDIDATE`, `CONTACTED`, `QUOTED`, `VERIFYING`, `APPROVED`, `REJECTED` |
| `EventKind` | `NOTE`, `CALL`, `MESSAGE`, `VISIT`, `STATUS_CHANGE`, `ALERT` |
| `QuoteCondition` | `NEW_SEALED`, `USED`, `REFURBISHED` |
| `ProfileKey` | `smartphones`, `laptops`, `accessories`, `parts` (se pueden agregar más) |
| `AlertKind` | `QUEUE_PAUSED`, `PARSER_BROKEN`, `SUPPLIER_STATUS_CHANGED`, `DATA_STALE`, `BACKUP_MISSING` |

## 3. Mapa de endpoints

**Rol mínimo:** `V` = viewer · `A` = analyst · `D` = admin. **Fase** según `docs/10`.

> Hoy solo existe `admin` (D-10). Las columnas de rol describen el diseño para cuando haya más usuarios.

| Método y ruta | Rol | Descripción | Fase |
| --- | --- | --- | --- |
| **Sesión** | | | |
| `POST /auth/login` | — | Iniciar sesión | H3 |
| `POST /auth/logout` | V | Cerrar sesión | H3 |
| `GET /auth/me` | V | Usuario actual | H3 |
| `POST /auth/change-password` | V | Cambiar la contraseña propia | H3 |
| `POST /auth/invitations/accept` | — | Aceptar invitación y fijar contraseña | H3 |
| **Usuarios** | | | |
| `GET /users` | D | Listar | H3 |
| `POST /users/invitations` | D | Invitar a un usuario | H3 |
| `PATCH /users/{id}` | D | Cambiar rol o activar o desactivar | H3 |
| `POST /users/{id}/reset-password` | D | Generar enlace de restablecimiento | H3 |
| **Importadores** | | | |
| `GET /importers` | V | Listado con filtros | H3 |
| `GET /importers/{ruc}` | V | Ficha completa | H3 |
| `GET /importers/export` | A | Exportar la vista filtrada (CSV o XLSX) | H3 |
| `POST /importers/{ruc}/lookup` | A | Encolar o forzar reconsulta | H3 |
| `PUT /importers/{ruc}/profile` | A | Cargar ficha a mano (en H2 se hace por CLI) | H3 |
| `POST /importers/{ruc}/exclude` | A | Excluir con motivo | H3 |
| `DELETE /importers/{ruc}/exclude` | A | Restaurar | H3 |
| **Pipeline** | | | |
| `GET /dashboard/funnel` | V | Embudo con conteos | H3 |
| `GET /pipeline/runs` | V | Ejecuciones | H3 |
| `GET /pipeline/runs/{id}` | V | Detalle de una ejecución | H3 |
| `POST /pipeline/runs` | A o D | Lanzar una ejecución (`INGEST_*` solo D) | H3 |
| `POST /pipeline/runs/{id}/cancel` | D | Cancelar | H3 |
| `POST /pipeline/uploads` | D | Subir archivo (lista o padrón) | H3 |
| `GET /pipeline/queue` | V | Estado de la cola | H3 |
| `PATCH /pipeline/queue` | A o D | Pausar o reanudar (A) · cambiar tope y ritmo (D) | H3 |
| `GET /pipeline/tasks` | V | Tareas de consulta, filtrables por estado | H3 |
| `POST /pipeline/tasks/{id}/cancel` | A | Cancelar una tarea | H3 |
| **Puntaje** | | | |
| `GET /scoring/profiles` | V | Perfiles y versiones | H3 |
| `POST /scoring/profiles` | D | Crear versión nueva | H3 |
| `POST /scoring/profiles/{id}/activate` | D | Activar versión | H3 |
| `GET /ciiu` | V | Catálogo | H3 |
| `PUT /ciiu/{code}` | D | Crear o editar un código | H3 |
| `GET /ciiu/unclassified` | V | Códigos vistos sin clasificar | H3 |
| **Proveedores** | | | |
| `GET /suppliers` | V | Listado | H4 |
| `POST /suppliers` | A | Crear desde un RUC | H4 |
| `GET /suppliers/{id}` | V | Ficha | H4 |
| `PATCH /suppliers/{id}` | A | Editar contacto, responsable, notas | H4 |
| `POST /suppliers/{id}/transition` | A | Cambiar de estado | H4 |
| `PATCH /suppliers/{id}/checklist` | A | Marcar ítems | H4 |
| `GET /suppliers/{id}/events` | V | Línea de tiempo | H4 |
| `POST /suppliers/{id}/events` | A | Agregar evento | H4 |
| `GET /suppliers/{id}/quotes` | V | Cotizaciones | H4 |
| `POST /suppliers/{id}/quotes` | A | Agregar cotización | H4 |
| `GET /quotes/compare` | V | Comparar cotizaciones por producto | H4 |
| `GET /suppliers/export` | A | Exportar | H4 |
| `GET /checklist-templates` | V | Plantillas de verificación | H4 |
| **Administración** | | | |
| `GET /audit` | D | Registro de auditoría | H3 |
| `GET /alerts` | V | Avisos abiertos (campana y banners). `?open=true` por defecto | H3 |
| `POST /alerts/{id}/dismiss` | A | Descartar un aviso | H3 |
| `GET /health` · `GET /ready` | — | Salud y disponibilidad (fuera de `/api/v1`) | H3 |

## 4. Detalle de los endpoints principales

### 4.1 `POST /auth/login`

Solicitud:
```json
{ "email": "analista@ejemplo.pe", "password": "********" }
```
Respuesta `200` (fija las cookies de sesión y de CSRF):
```json
{ "id": "5f0c…", "email": "analista@ejemplo.pe", "name": "Ana", "role": "analyst" }
```
Errores: `401 UNAUTHENTICATED` con un mensaje **genérico** («Correo o contraseña incorrectos. Tras varios intentos fallidos la cuenta se bloquea por 15 minutos») y `429 RATE_LIMITED`. Una cuenta bloqueada responde **igual** que una contraseña incorrecta, para no revelar si el correo existe.

### 4.2 `GET /importers`

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `q` | texto | Busca por RUC (exacto o prefijo) o por razón social (tolerante a tildes y errores) |
| `stage` | lista de `Stage` | Etapas |
| `discard_reason` | lista | Motivos de descarte |
| `estado`, `condicion` | texto | Valores de SUNAT |
| `ruc_kind` | `JURIDICA`, `NATURAL`, `OTRO` | Tipo de RUC |
| `profile_id` | entero | Perfil con el que se calcula el nivel. Por defecto, el perfil activo cuyo `key` es `default_profile_key` (`smartphones` al inicio) |
| `tier` | lista de `Tier` | Niveles |
| `min_score` | entero | Puntaje mínimo |
| `ciiu` | lista de códigos | Con alguna actividad en esos códigos |
| `departamento` | texto o ubigeo | Por prefijo de ubigeo |
| `comercio_exterior` | `IMPORTADOR`, `EXPORTADOR` | Actividad de comercio exterior |
| `is_supplier` | booleano | Ya está en proveedores |
| `excluded` | booleano | Incluye excluidos (por defecto `false`) |
| `sort` | texto | `score`, `razon_social`, `aduanet_last_update`, `fecha_inscripcion`, `priority` |

Respuesta `200`:
```json
{
  "items": [
    {
      "ruc": "20526185847",
      "razon_social": "SERVICIOS GENERALES HUZA & OÑA E.I.R.L",
      "ruc_kind": "JURIDICA",
      "stage": "DISCARDED",
      "discard_reason": "ESTADO_NO_ACTIVO",
      "estado": "BAJA DE OFICIO",
      "condicion": "HABIDO",
      "aduanet_last_update": "2014-01-27",
      "aduanet_appearances": 4,
      "score": null,
      "tier": null,
      "is_supplier": false,
      "excluded": false
    }
  ],
  "page": 1, "page_size": 50, "total": 1
}
```

### 4.3 `GET /importers/{ruc}`

```json
{
  "ruc": "20526185847",
  "razon_social": "SERVICIOS GENERALES HUZA & OÑA E.I.R.L",
  "razon_social_original": "\" SERVICIOS GENERALES HUZA & OÑA E.I.R.L \"",
  "ruc_kind": "JURIDICA",
  "stage": "DISCARDED",
  "discard_reason": "ESTADO_NO_ACTIVO",
  "aduanet": { "last_update": "2014-01-27", "appearances": 4, "snapshot_id": 3 },
  "padron": { "estado": "BAJA DE OFICIO", "condicion": "HABIDO", "ubigeo": "200101", "checked_at": "2026-10-25T10:00:00Z" },
  "profile": {
    "source": "SUNAT_WEB",
    "tipo_contribuyente": "EMPRESA INDIVIDUAL DE RESP. LTDA",
    "fecha_inscripcion": "2010-08-20",
    "fecha_baja": "2024-10-31",
    "comercio_exterior": ["IMPORTADOR", "EXPORTADOR"],
    "comprobantes_autorizados": ["FACTURA", "BOLETA DE VENTA"],
    "fetched_at": "2026-10-25T10:05:00Z"
  },
  "activities": [
    { "kind": "PRINCIPAL",  "ciiu_code": "4923", "description": "TRANSPORTE DE CARGA POR CARRETERA" },
    { "kind": "SECUNDARIA", "ciiu_code": "7730", "description": "ALQUILER Y ARRENDAMIENTO DE OTROS TIPOS DE MAQUINARIA, EQUIPO Y BIENES TANGIBLES" },
    { "kind": "SECUNDARIA", "ciiu_code": "4663", "description": "VENTA AL POR MAYOR DE MATERIALES DE CONSTRUCCIÓN, ARTÍCULOS DE FERRETERÍA Y EQUIPO Y MATERIALES DE FONTANERÍA Y CALEFACCIÓN" }
  ],
  "status_history": [
    { "estado": "BAJA DE OFICIO", "condicion": "HABIDO", "observed_at": "2026-10-25T10:00:00Z" }
  ],
  "scores": [],
  "open_task": null,
  "supplier_id": null,
  "official_lookup_url": "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"
}
```

Para un importador puntuado, `scores` trae, por perfil activo:
```json
{ "profile_id": 1, "profile_name": "Smartphones / iPhone", "profile_version": 1,
  "score": 85, "tier": "A", "computed_at": "…",
  "breakdown": { "gates": {…}, "items": [ { "key": "rubro", "points": 40, "max": 40, "note": "4652 principal, peso 1.0" } ], "total": 85 } }
```
> El campo `ubigeo` del ejemplo es ilustrativo. Los datos de domicilio fiscal de personas jurídicas se muestran; los de personas naturales (`ruc_kind = NATURAL`) siguen las reglas de `docs/07` §7.

### 4.4 `POST /importers/{ruc}/lookup`

Solicitud: `{ "force": false }`.
- `202` con `{ "task_id": 981 }` si se encoló.
- `200` con `{ "cached": true, "fetched_at": "…" }` si la ficha está dentro del TTL y `force` es `false`.
- `409 CONFLICT` si el importador está `DISCARDED` o ya tiene una tarea abierta.
- Si la cola está pausada o se alcanzó el tope diario, la tarea **igual se encola** y la respuesta `202` incluye `"queue_paused": true` o `"daily_cap_reached": true` para que la interfaz lo avise.

### 4.5 `PUT /importers/{ruc}/profile` (ficha manual)

Resuelve una tarea `NEEDS_HUMAN`. Los campos mínimos son `estado`, `condicion`, `comercio_exterior` y al menos una actividad con `kind = PRINCIPAL`:

```json
{
  "tipo_contribuyente": "SOCIEDAD ANONIMA CERRADA",
  "fecha_inscripcion": "2015-03-12",
  "estado": "ACTIVO",
  "fecha_baja": null,
  "condicion": "HABIDO",
  "comercio_exterior": ["IMPORTADOR"],
  "comprobantes_autorizados": ["FACTURA"],
  "activities": [ { "kind": "PRINCIPAL", "ciiu_code": "4652" } ]
}
```
Respuesta `200` con la ficha guardada, `source = MANUAL`, y la tarea cerrada como `DONE`. Se registra en la auditoría.

### 4.6 `POST /pipeline/runs`

```json
{ "kind": "INGEST_ADUANET", "params": { "source": "fetch" } }
```
```json
{ "kind": "INGEST_PADRON", "params": { "source": "upload", "upload_id": "9b1e…" } }
```
```json
{ "kind": "ENQUEUE_LOOKUPS", "params": { "limit": 400, "min_priority": 40 } }
```
```json
{ "kind": "SCORE", "params": { "profile_id": 1 } }
```
Respuesta `202`: `{ "run_id": 42 }`.
Errores: `403` si el rol no alcanza para ese `kind`, `409 ALREADY_PROCESSED` si el archivo ya se procesó, `409 CONFLICT` si ya hay una ejecución del mismo tipo en curso.

### 4.7 `GET /pipeline/runs/{id}`

```json
{
  "id": 42, "kind": "INGEST_ADUANET", "status": "SUCCEEDED",
  "triggered_by": { "id": "5f0c…", "name": "Ana" },
  "started_at": "2026-10-25T14:00:00Z", "finished_at": "2026-10-25T14:03:10Z",
  "stats": { "rows_read": 48210, "unique_rucs": 41377, "new": 41377, "invalid": 12, "duplicates_merged": 6821 },
  "error": null
}
```

### 4.8 `GET /pipeline/queue` y `PATCH /pipeline/queue`

```json
{
  "paused": true,
  "pause_reason": "HUMAN_VERIFICATION",
  "daily_cap": 400,
  "done_today": 137,
  "counts": { "QUEUED": 2610, "RUNNING": 0, "NEEDS_HUMAN": 1, "FAILED": 9 },
  "delay_min_s": 6, "delay_max_s": 12, "ttl_days": 30
}
```
`PATCH` acepta `paused` (analista o admin) y `daily_cap`, `delay_min_s`, `delay_max_s`, `ttl_days` (solo admin). Los límites son `delay_min_s ≥ 3` y `daily_cap ≤ 1000`; fuera de rango responde `422`.

### 4.9 `GET /dashboard/funnel?profile_id=1`

```json
{
  "total_unique": 41377,
  "stages": { "INGESTED": 0, "PADRON_CHECKED": 14120, "QUEUED": 2610, "LOOKED_UP": 310, "SCORED": 1450, "DISCARDED": 22887 },
  "discarded_by_reason": { "ESTADO_NO_ACTIVO": 19302, "CONDICION_NO_HABIDO": 2410, "NO_ENCONTRADO_EN_PADRON": 940, "SIN_ACTIVIDAD_IMPORTADOR": 3, "EXCLUIDO_MANUAL": 232 },
  "tiers": { "A": 38, "B": 142, "C": 410, "D": 860 },
  "suppliers": { "CANDIDATE": 12, "CONTACTED": 6, "QUOTED": 3, "VERIFYING": 2, "APPROVED": 1, "REJECTED": 4 },
  "last_snapshots": { "ADUANET_LIST": "2026-10-24", "PADRON_REDUCIDO": "2026-10-25" }
}
```
> Los números son **ilustrativos**. Los reales se miden en el spike.

### 4.10 `POST /scoring/profiles`

Crea una versión nueva a partir de un `config` válido (el servidor lo valida contra el esquema de `docs/05` §6.1):
```json
{ "key": "smartphones", "name": "Smartphones / iPhone", "config": { "…": "…" } }
```
Respuesta `201` con `version` autoincrementada y `is_active: false`. `POST /scoring/profiles/{id}/activate` la activa y desactiva la anterior, y devuelve `202` con el `run_id` del `SCORE` que recalcula los puntajes.

### 4.11 `POST /suppliers`

```json
{ "ruc": "20525210686", "categories": ["smartphones", "laptops"], "contact_name": "…", "whatsapp": "+51 …", "checklist_template_id": 1 }
```
Respuesta `201` con el proveedor en `CANDIDATE`. `409 CONFLICT` si el RUC ya es proveedor, está `DISCARDED` o excluido. `GET /suppliers` acepta los filtros `status`, `category`, `owner_id` y `q`.

### 4.12 `POST /suppliers/{id}/transition`

```json
{ "to": "APPROVED", "reason": null }
```
Reglas: `REJECTED` exige `reason`. `APPROVED` exige la lista de verificación completa: si faltan puntos, responde `409 CHECKLIST_INCOMPLETE` con `"pending": ["factura_electronica", "referencias"]`. Solo se permiten las transiciones de `docs/08` F4 (avanzar, saltando pasos si hace falta, ir a `REJECTED`, o reabrir un rechazado a `CANDIDATE`). Cualquier otra responde `409 CONFLICT`. Todo cambio genera un evento `STATUS_CHANGE`.

### 4.13 `PATCH /suppliers/{id}/checklist`

```json
{ "items": { "ruc_activo": { "done": true, "note": "Verificado en consulta SUNAT el 25/10" } } }
```
El servidor completa `by` y `at`.

### 4.14 `POST /suppliers/{id}/quotes` y `GET /quotes/compare`

```json
{ "category": "smartphones", "product": "iPhone 14 Pro", "storage": "256 GB",
  "condition": "REFURBISHED", "grade": "A", "battery_health_pct": 91,
  "unit_price": 680.00, "currency": "USD", "min_qty": 10, "includes_igv": false,
  "warranty_days": 90, "lead_time_days": 7, "stock_qty": 40, "valid_until": "2026-11-05" }
```
`GET /quotes/compare?category=smartphones&product=iPhone%2014%20Pro&storage=256%20GB&condition=REFURBISHED` devuelve la cotización **vigente más reciente** de cada proveedor, ordenadas por precio, con la moneda original y sin convertir (la conversión es decisión humana). Para usados y reacondicionados se puede filtrar además por `grade` y `min_battery_health_pct`. La respuesta incluye garantía, plazo de entrega y stock para poder comparar.

### 4.15 `GET /importers/export` y `GET /suppliers/export`

Aceptan los mismos filtros que el listado más `format=csv|xlsx`. Respuesta en flujo continuo con `Content-Disposition: attachment; filename="importadores-2026-10-25.csv"`. Cada exportación queda en la auditoría con los filtros usados. El CSV usa UTF-8 con BOM (para abrir bien en Excel) y `;` como separador cuando `locale=es-PE`.

## 5. Autorización por rol (resumen)

La matriz completa está en `docs/07` §4. Regla de oro: **el servidor decide**; ocultar un botón en la interfaz no es seguridad.

**Enmascarado para `viewer`:** en las respuestas de `/suppliers` y `/suppliers/{id}`, los campos `phone`, `whatsapp`, `email` y `address` llegan enmascarados (`"+51 9•• ••• 123"`) cuando el proveedor es una persona natural (`ruc_kind = NATURAL`). El servidor los enmascara, no la interfaz.

## 6. Versionado y cambios

- Los cambios compatibles (campos nuevos opcionales) no suben de versión.
- Un cambio incompatible crea `/api/v2` y mantiene `/api/v1` hasta migrar el cliente.
- La integración continua compara el OpenAPI generado con el archivo `openapi.json` versionado en el repositorio. Si difiere, falla hasta que se actualice a propósito.
