# 11 · Estructura de proyecto

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Fuente:** `docs/04` (arquitectura) y `docs/10` (plan).
**Estado:** propuesta. **Todavía no existe código.** Este documento fija el árbol y las convenciones para empezar sin discutirlas en cada archivo.

---

## 1. Decisión de forma

**Monorepo** con dos aplicaciones (`backend` y `web`), infraestructura y documentación en el mismo repositorio. Un solo lugar, una sola integración continua y un solo contrato de API compartido.

## 2. Árbol de carpetas

```
bot-scraping/
├─ README.md
├─ CLAUDE.md                      Contexto para Claude Code: reglas del proyecto y enlaces a docs/
├─ Makefile                       Atajos: make up, make test, make lint, make openapi…
├─ docker-compose.yml             Desarrollo: postgres, redis, api, worker, web
├─ docker-compose.prod.yml        Solo si algún día se despliega: agrega caddy y límites
├─ .env.example                   Variables sin valores reales
├─ .gitignore                     Incluye .env, data/, node_modules, __pycache__
├─ .pre-commit-config.yaml        ruff, mypy, prettier, escáner de secretos
├─ openapi.json                   Contrato versionado (se compara en la integración continua)
│
├─ docs/                          Documentación (esta carpeta)
│  ├─ 01-contexto-y-analisis.md … 11-estructura-de-proyecto.md
│  └─ decisiones/                 ADR nuevos, uno por archivo, cuando crezca el registro
│
├─ backend/                       Python 3.12 o superior · gestionado con uv
│  ├─ pyproject.toml              Dependencias, ruff, mypy, pytest, import-linter
│  ├─ alembic.ini
│  ├─ alembic/
│  │  └─ versions/                Migraciones
│  ├─ src/radar/
│  │  ├─ __init__.py
│  │  ├─ main.py                  App FastAPI
│  │  ├─ worker.py                Configuración de arq (funciones y cron)
│  │  ├─ cli.py                   Comandos `radar` (Typer)
│  │  ├─ core/
│  │  │  ├─ config.py             Configuración desde variables de entorno
│  │  │  ├─ db.py                 Motor y sesión de SQLAlchemy
│  │  │  ├─ security.py           Hash de contraseñas, tokens, CSRF
│  │  │  ├─ logging.py            Registros JSON con filtro de datos sensibles
│  │  │  ├─ errors.py             Excepciones y formato RFC 9457
│  │  │  └─ ruc.py                Validación y normalización de RUC
│  │  ├─ auth/                    router.py · service.py · models.py · schemas.py · deps.py
│  │  ├─ importers/               router.py · service.py · models.py · schemas.py · search.py
│  │  ├─ ingest/
│  │  │  ├─ aduanet.py            Parser de la lista (HTML y CSV)
│  │  │  ├─ padron.py             Lector en streaming del padrón
│  │  │  ├─ snapshots.py          Archivos, hashes y registro
│  │  │  └─ service.py
│  │  ├─ lookup/
│  │  │  ├─ queue.py              Reclamo de tareas, estados, pausa y tope
│  │  │  ├─ pacing.py             Ritmo cortés y reintentos
│  │  │  ├─ parser.py             HTML de la consulta → datos validados
│  │  │  ├─ service.py
│  │  │  └─ providers/
│  │  │     ├─ base.py            Interfaz RucProvider y ProviderResult
│  │  │     ├─ sunat_web.py       Playwright (un RUC a la vez)
│  │  │     ├─ manual.py
│  │  │     ├─ third_party.py     Opcional
│  │  │     └─ official_api.py    Opcional
│  │  ├─ scoring/
│  │  │  ├─ engine.py             Función pura de puntaje
│  │  │  ├─ profiles.py           Esquema y validación del `config`
│  │  │  ├─ ciiu.py
│  │  │  └─ service.py
│  │  ├─ suppliers/               router · service · models · schemas · checklist.py · quotes.py
│  │  ├─ pipeline/                runs.py · funnel.py · schedules.py · router.py
│  │  └─ audit/                   service.py · models.py · router.py
│  ├─ tests/
│  │  ├─ unit/
│  │  ├─ integration/             Con PostgreSQL y Redis reales (Testcontainers)
│  │  ├─ contract/                Proveedores y OpenAPI
│  │  └─ fixtures/
│  │     ├─ aduanet/              lista_muestra.html · lista_con_duplicados.html · lista_invalida.csv
│  │     ├─ padron/               padron_muestra.zip (sintético) · padron_truncado.zip
│  │     └─ consulta_ruc/         ruc_baja_de_oficio.html · ruc_activo_sac.html · ruc_persona_natural.html · ruc_sin_actividades.html
│  └─ Dockerfile                  Imagen de api y worker (con Chromium para el worker)
│
├─ web/                           Next.js (App Router) · TypeScript estricto · pnpm
│  ├─ package.json
│  ├─ next.config.ts
│  ├─ tailwind.config.ts          Tokens de docs/09
│  ├─ src/
│  │  ├─ app/
│  │  │  ├─ (auth)/login · aceptar-invitacion/[token]
│  │  │  └─ (app)/
│  │  │     ├─ page.tsx           Panel
│  │  │     ├─ importadores/      page.tsx · [ruc]/page.tsx
│  │  │     ├─ proveedores/       page.tsx · [id]/page.tsx · comparar/page.tsx
│  │  │     ├─ procesos/
│  │  │     └─ ajustes/           perfiles · ciiu · usuarios · auditoria · cuenta
│  │  ├─ components/
│  │  │  ├─ ui/                   Piezas base (botón, campo, tabla, diálogo)
│  │  │  └─ domain/               EstadoBadge, TierBadge, Funnel, ScoreBreakdown, QueueBanner, Timeline…
│  │  ├─ lib/
│  │  │  ├─ api/                  Cliente generado desde openapi.json
│  │  │  ├─ format.ts             Fechas, moneda y números es-PE
│  │  │  └─ permissions.ts        Qué ve cada rol
│  │  └─ styles/tokens.css        Variables CSS de docs/09
│  ├─ tests/                      Vitest y Playwright
│  └─ Dockerfile
│
├─ infra/
│  ├─ caddy/Caddyfile
│  ├─ backup/                     backup.sh · restore.sh · plist de launchd (opcional)
│  └─ postgres/init.sql           Extensiones
│
├─ scripts/
│  ├─ dev_seed.py                 Datos de ejemplo para desarrollo
│  ├─ gen_openapi.sh              Genera openapi.json y el cliente de web/
│  └─ spike/                      Scripts desechables de la semana 1 (se borran o archivan)
│
├─ data/                          NO se versiona. Archivos originales y respuestas crudas
│  └─ raw/                        aduanet/ · padron/ · lookups/
│
└─ .github/workflows/
   ├─ ci.yml                      Formato, tipos, pruebas, OpenAPI, secretos, auditoría
   └─ deploy.yml                  Construir imágenes y desplegar
```

## 3. Responsabilidad de cada pieza

| Carpeta | Responsabilidad | No debe |
| --- | --- | --- |
| `backend/src/radar/core` | Cosas transversales | Importar de otros módulos de dominio |
| `…/auth`, `importers`, `suppliers`, `pipeline`, `audit` | Dominio + API de ese dominio | Leer las tablas de otro módulo |
| `…/ingest` | Leer fuentes masivas y dejarlas en `importers` | Hacer consultas individuales a SUNAT |
| `…/lookup` | Cola de consultas y proveedores | Calcular puntajes |
| `…/scoring` | Puntaje como función pura | Acceder a la base de datos o a la red |
| `web/src/components/domain` | Piezas con significado de negocio | Llamar a la API directamente (usan hooks de `lib/api`) |
| `infra` | Despliegue y respaldos | Contener secretos |

Las reglas de dependencia se aplican con **`import-linter`** en `backend/pyproject.toml` y fallan la integración continua si se rompen.

## 4. Convenciones

### 4.1 Nombres

| Elemento | Convención | Ejemplo |
| --- | --- | --- |
| Dominio SUNAT | **Español** | `ruc`, `razon_social`, `estado`, `condicion`, `ubigeo` |
| Infraestructura y lógica | **Inglés** | `stage`, `score`, `lookup_task`, `created_at` |
| Python | `snake_case` (funciones y módulos), `PascalCase` (clases) | `score_importer()` |
| TypeScript | `camelCase` (variables), `PascalCase` (componentes) | `ScoreBreakdown` |
| Archivos de documentación | `NN-nombre-en-minusculas.md` | `04-arquitectura-de-software.md` |
| Tablas | Plural en inglés, `snake_case` | `importers`, `lookup_tasks` |
| Enumeraciones | `MAYUSCULAS_CON_GUION_BAJO` | `NEEDS_HUMAN`, `ESTADO_NO_ACTIVO` |
| Rutas web | Español en minúsculas | `/importadores`, `/proveedores` |

### 4.2 Idiomas

- **Interfaz y documentación:** español del Perú.
- **Código, nombres técnicos, mensajes de commit y comentarios:** inglés, salvo términos del dominio SUNAT.
- **Formatos:** fechas `dd/mm/aaaa` en la interfaz y ISO 8601 en la API y la base de datos. Números en `es-PE`: punto decimal y coma de miles (`S/ 1,250.50`).

### 4.3 Git

- Rama principal `main`, siempre desplegable. Ramas cortas `feat/…`, `fix/…`, `docs/…`.
- **Conventional Commits.** Ejemplo: `feat(ingest): deduplicate importers by RUC`.
- Cada solicitud de cambios incluye: qué cambia, cómo se probó y qué documento se actualizó.
- Nunca se commitean `.env`, archivos de `data/` ni respuestas crudas de SUNAT.

### 4.4 Calidad

| Herramienta | Uso |
| --- | --- |
| `ruff` | Formato y análisis estático del backend |
| `mypy --strict` | Tipos del backend |
| `pytest` + `pytest-cov` | Pruebas. Umbral de cobertura en módulos críticos |
| `import-linter` | Reglas de dependencia entre módulos |
| `eslint` + `prettier` | Frontend |
| TypeScript `strict` | Frontend |
| `gitleaks` (o similar) | Escáner de secretos |
| `pip-audit` y `pnpm audit` | Dependencias |

## 5. Línea de comandos `radar`

```
radar ingest aduanet [--file RUTA | --fetch]      # lista de importadores
radar ingest padron  [--file RUTA | --fetch]      # estado y condición
radar funnel                                      # embudo en consola
radar enqueue  [--limit 400] [--min-priority 40]  # encolar consultas
radar lookup run [--max 50]                       # procesar la cola con ritmo cortés
radar lookup manual RUC --from-file ficha.json    # cargar ficha a mano
radar queue pause|resume|status
radar score [--profile smartphones]               # recalcular puntajes
radar export --stage SCORED --tier A,B --profile smartphones --out proveedores.csv
radar smoke RUC                                   # consulta real de prueba (manual)
radar admin create EMAIL                          # crea el primer administrador
radar db migrate                                  # aplica migraciones
radar backup [--out RUTA]                         # copia cifrada de la base de datos
radar restore RUTA                                # restaura una copia
radar disk                                        # huella en disco (Docker, base y archivos)
```

## 6. `Makefile` (atajos previstos)

| Comando | Qué hace |
| --- | --- |
| `make up` / `make down` | Levanta o apaga el entorno con Docker Compose |
| `make migrate` | Aplica migraciones |
| `make seed` | Carga semillas y datos de ejemplo |
| `make test` | Pruebas del backend y de la web |
| `make lint` | Formato, tipos y reglas de dependencia |
| `make openapi` | Regenera `openapi.json` y el cliente de la web |
| `make backup` / `make restore` | Respaldo y restauración locales |

## 7. Servicios de Docker Compose

| Servicio | Imagen | Puerto interno | Notas |
| --- | --- | --- | --- |
| `postgres` | `postgres:16` | 5432 | Volumen `pgdata`. Sin puerto público |
| `redis` | `redis:7` | 6379 | Volumen `redisdata`. Sin puerto público |
| `api` | `backend` | 8000 | Sin Chromium |
| `worker` | `backend` (con navegador) | — | Un solo proceso de consultas |
| `web` | `web` | 3000 | — |
| `caddy` | `caddy:2` | 80, 443 | Solo si algún día se expone fuera de tu equipo |
| `backup` | — | — | Ya no es un servicio: se usa `radar backup` (programable con `launchd`) |

**Modo local:** `postgres` y `redis` van en Docker. `api`, `worker` y `web` pueden correr en Docker o directamente en tu Mac (`uv run`, `pnpm dev`), según la huella en disco que se mida en el spike (SP-11).

## 8. Archivos de apoyo para Claude Code

`CLAUDE.md` en la raíz resume lo que cualquier sesión de trabajo debe respetar:

- Qué es el proyecto y dónde están los documentos (`docs/`).
- **Líneas rojas:** no evadir captchas ni bloqueos, no consultar en paralelo a SUNAT, no usar Clave SOL, no guardar secretos en el repositorio.
- Convenciones de nombres (§4.1) y de commits (§4.3).
- Cómo ejecutar pruebas y regenerar el OpenAPI.
- Que los parsers se prueban solo con *fixtures*.

## 9. Primeros pasos para arrancar

1. Crear el repositorio y copiar `docs/` y `README.md`. Agregar `.gitignore` y `.env.example`.
2. Hacer el **spike** (`docs/10` §4) y guardar los archivos como *fixtures* en `backend/tests/fixtures/`.
3. Generar la estructura de `backend/` con `uv init` y de `web/` con `create-next-app`.
4. `docker-compose.yml` con PostgreSQL y Redis. Primera migración con las tablas de `docs/05` §3 y §4.
5. Implementar `core/ruc.py` con sus pruebas (los 16 RUC de las capturas pasan la validación y uno con el dígito alterado falla).
6. Implementar el parser de Aduanet con el `fixture` real.
7. Implementar el lector del padrón con un archivo sintético.
8. Dejar listo `radar export` para entregar **H1**.

## 10. Qué se versiona y qué no

| Se versiona | No se versiona |
| --- | --- |
| Código, migraciones, `docs/`, `openapi.json`, `.env.example`, *fixtures* pequeños y anonimizados | `.env`, `data/`, respaldos, respuestas crudas, claves, bases de datos locales |

> **Sobre los *fixtures*:** los HTML de SUNAT contienen datos de empresas (públicos) y, a veces, de personas naturales. Para el repositorio se usan **muestras recortadas** y, en el caso de personas naturales, **sintéticas**. Los archivos completos viven solo en `data/`.
