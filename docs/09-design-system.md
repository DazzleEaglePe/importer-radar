# 09 · Design system

**Versión:** 0.2 (borrador) · **Fecha:** 25/10/2026
**Fuente:** `docs/08` (pantallas y flujos) y `docs/03` §7 (usabilidad y accesibilidad).
**Enfoque:** un sistema **pequeño y sobrio** para una herramienta de trabajo. Prioriza lectura rápida de tablas, estados inequívocos y accesibilidad. No es una marca: el nombre y el color de acento se pueden cambiar sin tocar los componentes, porque todo sale de **tokens**.
**Base técnica:** Tailwind CSS + shadcn/ui (Radix) + lucide-react + TanStack Table. Los tokens viven como variables CSS en `web/src/styles/tokens.css`.

---

## 1. Principios visuales

1. **La información manda.** Poco adorno, mucho contraste, tablas legibles.
2. **El estado se lee de un vistazo, sin depender del color.** Todo estado lleva texto y un ícono además del color.
3. **Consistencia antes que originalidad.** Un solo componente para cada cosa.
4. **Tema claro y oscuro** desde el inicio, siguiendo el sistema operativo.
5. **Cada color con propósito.** El acento (índigo) es para acciones y foco. El verde, el ámbar, el rojo y el celeste son **solo** para estados.

## 2. Tokens de color

Todos los pares de texto y fondo están **medidos** con la fórmula de contraste de WCAG. Meta: **4.5:1** para texto normal y **3:1** para bordes de controles, foco e íconos con significado.

### 2.1 Neutros y acento

| Token | Claro | Oscuro | Uso | Contraste (claro / oscuro) |
| --- | --- | --- | --- | --- |
| `--bg` | `#FFFFFF` | `#020617` | Fondo de página | — |
| `--bg-subtle` | `#F8FAFC` | `#0F172A` | Fondos de secciones y cabecera de tabla | — |
| `--surface` | `#FFFFFF` | `#0F172A` | Tarjetas, diálogos | — |
| `--text` | `#0F172A` | `#F1F5F9` | Texto principal | 17.85 sobre `--bg` claro |
| `--text-muted` | `#475569` | `#CBD5E1` | Texto secundario | 7.58 / 12.02 |
| `--text-subtle` | `#64748B` | `#94A3B8` | Notas, fuentes de datos, placeholders | 4.76 sobre blanco, 4.55 sobre `--bg-subtle` / 6.96 |
| `--border` | `#E2E8F0` | `#334155` | Separadores **decorativos** (filas, tarjetas) | No identifica controles |
| `--border-strong` | `#7B8794` | `#7B8BA3` | **Bordes de campos y controles** | 3.66 sobre blanco / 5.16 sobre `#0F172A` |
| `--primary` | `#4F46E5` | `#818CF8` | Botón primario, selección | Texto blanco 6.29 / texto `#020617` 6.76 |
| `--primary-hover` | `#4338CA` | `#A5B4FC` | Hover del primario | — |
| `--primary-text` | `#FFFFFF` | `#020617` | Texto sobre el primario | — |
| `--link` | `#4338CA` | `#A5B4FC` | Enlaces | 7.90 / 8.96 |
| `--focus-ring` | `#4F46E5` | `#818CF8` | Anillo de foco (2 px + 2 px de separación) | 6.29 / 5.98 |

> **Atención:** el texto **blanco sobre verde 600** (`#16A34A`) da solo 3.30 y **no se usa** para texto. Los estados usan fondo tenue con texto oscuro (ver abajo).

### 2.2 Colores de estado (par fondo + texto)

| Token | Fondo claro | Texto claro | Contraste | Fondo oscuro | Texto oscuro | Contraste |
| --- | --- | --- | --- | --- | --- | --- |
| `--success` | `#DCFCE7` | `#166534` | 6.49 | `#052E16` | `#BBF7D0` | 12.30 |
| `--danger` | `#FEE2E2` | `#991B1B` | 6.80 | `#450A0A` | `#FECACA` | 11.16 |
| `--warning` | `#FEF3C7` | `#92400E` | 6.37 | `#451A03` | `#FDE68A` | 12.03 |
| `--info` | `#E0F2FE` | `#075985` | 6.59 | `#082F49` | `#BAE6FD` | 10.46 |
| `--neutral` | `#F1F5F9` | `#334155` | 9.45 | `#1E293B` | `#E2E8F0` | 11.87 |

### 2.3 Variables CSS (extracto)

```css
:root {
  --bg: #ffffff;           --bg-subtle: #f8fafc;     --surface: #ffffff;
  --text: #0f172a;         --text-muted: #475569;    --text-subtle: #64748b;
  --border: #e2e8f0;       --border-strong: #7b8794;
  --primary: #4f46e5;      --primary-hover: #4338ca; --primary-text: #ffffff;
  --link: #4338ca;         --focus-ring: #4f46e5;

  --success-bg: #dcfce7;   --success-fg: #166534;
  --danger-bg:  #fee2e2;   --danger-fg:  #991b1b;
  --warning-bg: #fef3c7;   --warning-fg: #92400e;
  --info-bg:    #e0f2fe;   --info-fg:    #075985;
  --neutral-bg: #f1f5f9;   --neutral-fg: #334155;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* mismos nombres con los valores oscuros */ }
}
:root[data-theme="dark"] { /* idem */ }
```

El modo se elige con `prefers-color-scheme` y puede forzarse desde *Mi cuenta* (`data-theme`).

## 3. Mapa de estados a colores e íconos

El **texto** siempre es el valor real (o su traducción). El ícono ayuda, nunca reemplaza el texto.

| Dato | Valor | Variante | Ícono (lucide) | Texto mostrado |
| --- | --- | --- | --- | --- |
| **Estado SUNAT** | `ACTIVO` | success | `circle-check` | ACTIVO |
| | `SUSPENSION TEMPORAL` | warning | `circle-pause` | SUSPENSIÓN TEMPORAL |
| | `BAJA PROVISIONAL`, `BAJA DEFINITIVA`, `BAJA DE OFICIO`, `BAJA PROV. POR OFICIO` | danger | `circle-x` | El valor tal cual |
| **Condición** | `HABIDO` | success | `map-pin` | HABIDO |
| | `PENDIENTE` | warning | `clock` | PENDIENTE |
| | `NO HABIDO`, `NO HALLADO` | danger | `map-pin-off` | El valor tal cual |
| **Nivel (tier)** | A | success | — (la letra) | Nivel A |
| | B | info | — | Nivel B |
| | C | warning | — | Nivel C |
| | D | neutral | — | Nivel D |
| **Etapa** | `INGESTED` | neutral | `circle-dashed` | En lista |
| | `PADRON_CHECKED` | info | `circle-check` | Elegible |
| | `QUEUED` | info | `clock` | En cola |
| | `LOOKED_UP` | info | `file-search` | Consultado |
| | `SCORED` | success | `badge-check` | Puntuado |
| | `DISCARDED` | neutral | `ban` | Descartado |
| **Tarea de consulta** | `QUEUED` | neutral | `clock` | En cola |
| | `RUNNING` | info | `loader-circle` (animado) | En curso |
| | `DONE` | success | `circle-check` | Hecha |
| | `FAILED` | danger | `triangle-alert` | Falló |
| | `NEEDS_HUMAN` | warning | `hand` | Requiere a una persona |
| | `CANCELLED` | neutral | `ban` | Cancelada |
| **Proveedor** | `CANDIDATE` | neutral | `user-plus` | Candidato |
| | `CONTACTED` | info | `message-circle` | Contactado |
| | `QUOTED` | info | `receipt` | Cotizó |
| | `VERIFYING` | warning | `shield-question` | En verificación |
| | `APPROVED` | success | `shield-check` | Aprobado |
| | `REJECTED` | danger | `shield-x` | Rechazado |
| **Condición del equipo** | `NEW_SEALED` | neutral | `package` | Nuevo sellado |
| | `REFURBISHED` | neutral | `refresh-cw` | Reacondicionado |
| | `USED` | neutral | `history` | Usado |
| **Cola** | Activa / Pausada | success / warning | `play` / `pause` | «Activa» / «Pausada · motivo» |
| **Aviso** | `info` / `warning` / `danger` | info / warning / danger | `info` / `triangle-alert` / `circle-alert` | El título del aviso |

## 4. Tipografía

| Rol | Fuente | Notas |
| --- | --- | --- |
| Interfaz | **Inter** (autoalojada con `next/font`) con `system-ui` de respaldo | Pesos 400, 500 y 600 |
| Cifras y códigos (RUC, CIIU, importes) | Inter con `font-variant-numeric: tabular-nums` | Los RUC y códigos se pueden mostrar en `ui-monospace` para copiar sin errores |

| Estilo | Tamaño / interlineado | Peso | Uso |
| --- | --- | --- | --- |
| `display` | 30 / 36 | 600 | Título de pantalla |
| `h1` | 24 / 32 | 600 | Encabezado de sección |
| `h2` | 20 / 28 | 600 | Subsección |
| `h3` | 16 / 24 | 600 | Título de tarjeta |
| `body` | 14 / 20 | 400 | Texto general y filas de tabla |
| `body-lg` | 16 / 24 | 400 | Texto de lectura |
| `caption` | 12 / 16 | 400 | Fuentes de datos, notas |
| `label` | 12 / 16 | 500 | Etiquetas de campos y encabezados de tabla (sin mayúsculas forzadas) |

Tamaño mínimo de texto: **12 px** (solo notas). Texto de acción y datos: **14 px o más**.

## 5. Espaciado, forma y elevación

| Token | Valor |
| --- | --- |
| Espaciado (base 4 px) | 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 |
| `--radius-sm` | 4 px (insignias pequeñas, casillas) |
| `--radius-md` | 6 px (botones, campos) |
| `--radius-lg` | 10 px (tarjetas, diálogos) |
| `--radius-pill` | 999 px (insignias y chips) |
| `--shadow-sm` | `0 1px 2px rgb(15 23 42 / 0.06)` |
| `--shadow-md` | `0 4px 12px rgb(15 23 42 / 0.10)` (menús y diálogos) |
| Ancho de contenido | Máximo 1280 px en pantallas anchas. Tablas a ancho completo |
| Rejilla | 12 columnas en escritorio, 8 en tablet, 4 en celular |
| Puntos de quiebre | 640 · 768 · 1024 · 1280 px |

## 6. Componentes

### 6.1 Acciones y entradas

| Componente | Variantes y reglas |
| --- | --- |
| **Button** | `primary`, `secondary`, `ghost`, `danger`. Tamaños `sm` (32 px), `md` (40 px) y `lg` (48 px). Estados: reposo, hover, foco, activo, deshabilitado y cargando. Una sola acción primaria por vista |
| **IconButton** | Siempre con `aria-label`. Área de toque mínima de 40 × 40 px |
| **TextField, Select, Combobox, MultiSelect** | Etiqueta visible arriba. Borde `--border-strong`. Texto de ayuda y de error debajo. Error con ícono y texto, no solo borde rojo |
| **SearchBox** | Ícono de lupa, botón para limpiar y atajo `/`. Busca con espera de 250 ms |
| **Checkbox, Radio, Switch** | Cajas de 20 px con área de clic ampliada |
| **FilterChips** | Chips con «×» para quitar. Un botón «+ Filtro» abre las opciones |
| **FileDropzone** | Para subir la lista y el padrón. Muestra nombre, tamaño y validación antes de enviar |

### 6.2 Datos

| Componente | Reglas |
| --- | --- |
| **DataTable** (TanStack Table) | Encabezado fijo, orden por columna con `aria-sort`, selección de filas, columnas configurables, paginación, densidad `cómoda` (40 px) y `compacta` (32 px), fila clicable con foco visible. Estados: cargando (filas esqueleto), vacío y error |
| **StatusBadge** | Recibe `kind` (estado, condición, nivel, etapa, tarea, proveedor) y `value`. Aplica la tabla de §3. Fondo y texto de los tokens de estado, ícono de 14 px, radio píldora |
| **ScoreMeter** | Barra de 5 segmentos **con el número escrito**. Al pasar el cursor o enfocar, muestra el desglose |
| **BreakdownList** | Lista de criterios con puntos obtenidos y máximos, una barra fina y la nota explicativa |
| **FunnelChart** | Barras horizontales con **cantidad y porcentaje escritos**. Cada barra es un enlace. Incluye una tabla equivalente oculta visualmente pero disponible para lectores de pantalla |
| **StatCard** | Número grande, rótulo y una acción. Sin gráficos decorativos |
| **DataFreshness** | Texto `caption` con la fuente y la antigüedad («SUNAT · consultado hace 3 días»). Pasa a `warning` si supera el umbral |
| **Timeline** | Eventos con ícono por tipo, autor, fecha relativa y fecha absoluta al enfocar |
| **QuoteTable** | Tabla específica para cotizaciones con precio alineado a la derecha, moneda explícita y etiqueta «Vencida» |

### 6.3 Estructura y navegación

| Componente | Reglas |
| --- | --- |
| **AppShell** | Barra superior con la navegación principal y el menú de usuario. Contenido a ancho máximo. En tablet, la navegación se pliega |
| **PageHeader** | Título, descripción corta, acciones a la derecha y *breadcrumbs* en las fichas |
| **Tabs** | Navegación por teclado con flechas. Pestaña activa con subrayado de 2 px **y** peso 600 |
| **Dialog / Drawer** | Atrapan el foco, se cierran con `Esc` y devuelven el foco al disparador. Los destructivos usan `ConfirmDialog` |
| **ConfirmDialog** | Título con la consecuencia, botón peligroso a la derecha y texto de lo que se pierde o cambia |
| **StatusPipeline** | Pasos del seguimiento de proveedor (Candidato → … → Aprobado), con el paso actual y las reglas visibles |

### 6.4 Comunicación

| Componente | Reglas |
| --- | --- |
| **Banner** (`info`, `warning`, `danger`, `success`) | Va arriba de la página, con ícono, mensaje, y **una acción**. Es el lugar de «Cola pausada», «Parser roto» y «Datos desactualizados». Anunciado con `role="status"` (o `alert` si es crítico) |
| **Toast** | Confirmaciones breves (5 s). Nunca para errores que requieren acción |
| **EmptyState** | Ícono sencillo, un titular, una frase y **la acción siguiente** |
| **Skeleton** | En lugar de *spinners* para tablas y tarjetas |
| **Tooltip** | Solo para información adicional. Nada esencial vive únicamente en un tooltip |
| **InlineHelp** | Texto de ayuda con ícono `info` y un enlace a la sección de la documentación |

### 6.5 Piezas de dominio

`CopyRuc` (copia el RUC con confirmación visual y para lectores de pantalla), `AlertBell` (campana con el número de avisos abiertos y un panel de lectura), `CategoryChips` (categorías de un proveedor), `SunatLink` (abre la consulta oficial en otra pestaña con `rel="noopener noreferrer"`), `QueueBanner`, `ChecklistItem`, `ContactActions` (enlaces a WhatsApp y teléfono, sin envío automático), `ProfilePicker` (selector del perfil de puntuación), `ImpactPreview` (cambios de nivel antes de guardar un perfil).

## 7. Patrones

| Patrón | Regla |
| --- | --- |
| **Fuente y fecha** | Todo dato que viene de SUNAT va acompañado de su fuente y antigüedad (`DataFreshness`) |
| **Explicar el puntaje** | El número nunca aparece solo: siempre un `ScoreMeter` con acceso al desglose |
| **Descartado** | Muestra el motivo en texto y en la cabecera. Nunca un nivel vacío sin explicación |
| **Acciones peligrosas** | Excluir, rechazar, cancelar ejecución y desactivar usuario piden confirmación con la consecuencia |
| **Esperas largas** | Estado en la página con avance por sondeo. Nunca bloquear la pantalla |
| **Errores** | Qué pasó + qué hacer + botón de reintento si aplica. Sin códigos internos |
| **Formularios** | Validación al salir del campo y al enviar. Resumen de errores arriba si hay más de uno, con enlaces a cada campo |
| **Aviso legal ligero** | La nota «El nivel se calcula con datos públicos… verifica antes de comprar» aparece en la ficha del importador y al aprobar un proveedor |

## 8. Formatos y contenido

| Elemento | Formato | Ejemplo |
| --- | --- | --- |
| Fecha en la interfaz | `dd/mm/aaaa` | 25/10/2026 |
| Fecha relativa | «hace 3 días» con la fecha exacta al enfocar | hace 3 días |
| Hora | 24 h, zona `America/Lima` | 14:03 |
| Números | `es-PE`: **punto decimal y coma de miles** | 41,377 · 0.7 % |
| Moneda | Símbolo antes del importe, con dos decimales | `S/ 1,250.00` · `US$ 1,050.00` |
| RUC | 11 dígitos sin espacios, en cifras tabulares | 20526185847 |
| Tono | Directo, en segunda persona («tú»), sin jerga técnica en la interfaz | «Cargar ficha a mano» |
| Siglas | Se explican la primera vez con un tooltip | CIIU, RUC, SUNAT |

Los textos de la interfaz viven en un archivo de mensajes (`es-PE`), no dentro de los componentes, para poder revisarlos juntos.

## 9. Accesibilidad (WCAG 2.1 AA)

| Verificación | Cómo |
| --- | --- |
| Contraste de texto ≥ 4.5:1 y de controles ≥ 3:1 | Valores de §2. Prueba automatizada sobre los tokens |
| Foco siempre visible | Anillo de 2 px con 2 px de separación, en todos los elementos interactivos |
| Teclado completo | Todo se alcanza y se opera con teclado. Orden de tabulación lógico. Atajos documentados y desactivables |
| Color nunca solo | Los estados llevan texto e ícono |
| Etiquetas y nombres | Todo control tiene nombre accesible. Los íconos decorativos van con `aria-hidden` |
| Tablas | `<th scope>`, `aria-sort`, resúmenes en tablas complejas |
| Avisos dinámicos | `aria-live="polite"` para cambios de cola y ejecuciones |
| Movimiento | Se respeta `prefers-reduced-motion`. Animaciones de 150 ms como máximo |
| Áreas táctiles | Mínimo 40 × 40 px en tablet |
| Zoom y reflujo | Funcional hasta 200 % de zoom y a 320 px de ancho, sin pérdida de información |
| Idioma | `lang="es-PE"` en el documento |
| Pruebas | `axe` automatizado en la integración continua más un recorrido manual con teclado y lector de pantalla antes de H5 |

## 10. Movimiento

| Uso | Duración | Curva |
| --- | --- | --- |
| Hover y foco | 100 ms | `ease-out` |
| Abrir y cerrar menús y diálogos | 150 ms | `ease-out` |
| Cambio de pestaña | Sin animación |  |
| Indicador de carga | Giro continuo del ícono `loader-circle`. Con movimiento reducido se reemplaza por texto «Cargando…» |  |

## 11. Implementación

1. `tokens.css` define las variables de §2 y las expone a Tailwind en `tailwind.config.ts` (`colors.primary = "var(--primary)"`).
2. Los componentes de `components/ui` son los de shadcn/ui ajustados a estos tokens. **No** se escriben colores en hexadecimal dentro de los componentes.
3. `StatusBadge` es el **único** lugar donde se traduce un valor de negocio a color e ícono (tabla de §3).
4. Una página de pruebas visuales (`/ajustes/diseno`, solo en desarrollo) muestra todos los componentes en claro y oscuro.
5. Las pruebas de contraste recorren los pares de §2 y fallan si alguno baja del umbral.
6. Cambiar el acento (por ejemplo, para una marca) obliga a **volver a medir** los pares que lo usan.
