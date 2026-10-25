# Radar de Importadores

> Panel interno que toma la lista oficial de importadores de SUNAT, descarta automáticamente a los que están de baja o no habidos, identifica a qué rubro se dedica cada uno y deja una lista corta de **proveedores locales confiables** para el primer lote de importación (iPhone) y los siguientes (laptops y dispositivos electrónicos en general).

**Estado:** Fase 0 — documentación previa. Todavía no hay código.
**Versión de la documentación:** 0.2 (borrador, 25/10/2026), armada a partir de las capturas de SUNAT, tus respuestas de arranque y tus respuestas a las preguntas abiertas.
**Nombre:** *Radar de Importadores* (confirmado el 25/10/2026). La carpeta se llama `bot-scraping` y el paquete de código usará `radar`.

---

## ¿Qué problema resuelve?

Vas a empezar a importar y necesitas **vendedores confiables**. SUNAT publica en Aduanet la *«Relación de Importadores que han actualizado sus datos»*, una lista enorme y alfabética de RUC, razón social y fecha de última actualización. Revisarla a mano es inviable, y la lista sola no dice si la empresa sigue activa ni a qué se dedica.

El ejemplo de tus capturas lo muestra: la primera fila de la lista, `20526185847`, está en **BAJA DE OFICIO** desde el 31/10/2024 y su rubro principal es transporte de carga. Aparece **4 veces** en la lista. Ese es el tipo de ruido que el sistema debe quitar solo.

## ¿Cómo lo resuelve?

Un embudo de cuatro pasos. Cada paso es más caro que el anterior, así que se aplica a cada vez menos empresas:

```
Lista Aduanet  →  Padrón reducido SUNAT  →  Consulta RUC puntual  →  Puntaje por rubro  →  Proveedores
 (RUC, nombre)    (ACTIVO y HABIDO, en     (rubro CIIU, antigüedad,   (perfil iPhone,        (contacto, cotización,
                   masa, sin scraping)      comercio exterior)         laptops, etc.)         verificación)
```

1. **Ingesta.** Se carga la lista de Aduanet, se limpia, se valida el dígito verificador de cada RUC y se quitan duplicados.
2. **Filtro en masa.** Se cruza con el [padrón reducido del RUC](https://orientacion.sunat.gob.pe/padron-reducido-del-ruc-para-descarga) que SUNAT ofrece para descarga. Quedan solo los **ACTIVO + HABIDO**. No hay que consultar uno por uno.
3. **Consulta puntual.** Solo a los que sobrevivieron, y por orden de prioridad, se consulta el RUC en SUNAT para leer la **actividad económica (CIIU)**, la fecha de inscripción y la actividad de comercio exterior.
4. **Puntaje.** Un perfil configurable (por ejemplo «Smartphones / iPhone») califica cada empresa con un desglose que se puede explicar y la ubica en un nivel A, B, C o D.
5. **Proveedores.** Desde el panel pasas empresas a tu lista de proveedores, registras contactos y cotizaciones, y completas una lista de verificación antes de aprobar.

## Lo que el sistema NO hace

- **No garantiza autenticidad.** Que una empresa esté activa, habida y registrada como importadora de electrónica es una *señal pública*, no una garantía de que venda iPhone originales ni de que sea distribuidor autorizado de Apple. Esa verificación es manual y está en el flujo.
- **No evade captchas ni bloqueos.** Si SUNAT pide verificación humana, la cola se pausa y la tarea queda para resolverla a mano.
- **No contacta a nadie por su cuenta.** No envía mensajes ni correos automáticos.
- **No es un ranking por volumen de importación.** La lista de Aduanet es de quienes *actualizaron datos*, no de «los más grandes». El volumen real requiere datos de comercio exterior que SUNAT no publica por empresa. Queda como mejora futura (ver `docs/01-contexto-y-analisis.md`).

## Decisiones tomadas

| Tema | Decisión |
| --- | --- |
| Rol de las empresas | **Proveedores locales** a quienes comprarles iPhone y luego otros dispositivos |
| Usuarios | **Interno**: solo tú, como administrador, por ahora. Roles e invitaciones quedan diseñados para cuando se sume más gente |
| Dónde corre | **En tu Mac**, sin VPS. Todo escucha solo en `127.0.0.1` |
| Fuente de datos RUC | **Padrón reducido** (masa) + **consulta puntual** (finalistas). Sin evadir captchas, sin Clave SOL y sin servicios de pago |
| Stack | **Python** (FastAPI, Playwright) + **Next.js** + **PostgreSQL** (con Redis para colas) |
| Confianza | `ACTIVO` y `HABIDO` obligatorios. Lo ideal son 5 años o más de antigüedad: con menos no se descarta, pero no pasa de nivel B |
| Productos | Primero **iPhone** (nuevos, reacondicionados y usados). Después laptops Apple, accesorios y cargadores, repuestos y baterías |
| Avisos | Solo **dentro del panel** |

## Documentación

| Archivo | Contenido |
| --- | --- |
| [`docs/01-contexto-y-analisis.md`](docs/01-contexto-y-analisis.md) | Origen, fuentes de datos, decisiones, riesgos y preguntas abiertas |
| [`docs/02-requerimientos-funcionales.md`](docs/02-requerimientos-funcionales.md) | Qué debe hacer el sistema, con criterios de aceptación |
| [`docs/03-requerimientos-no-funcionales.md`](docs/03-requerimientos-no-funcionales.md) | Rendimiento, seguridad, cortesía con las fuentes, costos |
| [`docs/04-arquitectura-de-software.md`](docs/04-arquitectura-de-software.md) | Componentes, flujo del pipeline, decisiones de arquitectura |
| [`docs/05-modelo-de-datos.md`](docs/05-modelo-de-datos.md) | Tablas, relaciones y SQL de referencia |
| [`docs/06-api-contract.md`](docs/06-api-contract.md) | Endpoints REST, esquemas y errores |
| [`docs/07-seguridad-y-auth.md`](docs/07-seguridad-y-auth.md) | Autenticación, roles, datos personales y conducta de scraping |
| [`docs/08-ux-flujos.md`](docs/08-ux-flujos.md) | Pantallas, flujos y estados |
| [`docs/09-design-system.md`](docs/09-design-system.md) | Tokens, componentes y accesibilidad |
| [`docs/10-plan-de-desarrollo.md`](docs/10-plan-de-desarrollo.md) | Fases, hitos, backlog y riesgos |
| [`docs/11-estructura-de-proyecto.md`](docs/11-estructura-de-proyecto.md) | Árbol de carpetas, convenciones y primeros pasos |

## Próximos pasos

1. Preguntas abiertas: respondidas el 25/10. Quedan tres matices en `docs/01-contexto-y-analisis.md` §9.3.
2. Hacer el **spike de la semana 1** (`docs/10`) en tu Mac: Aduanet ya respondió desde ahí. Falta bajar la lista completa y el padrón, y medir cuántas filas hay de verdad.
3. Entregar primero un **CSV filtrado sin interfaz** (hito H1). Con eso ya puedes empezar a contactar proveedores mientras se construye el panel.
