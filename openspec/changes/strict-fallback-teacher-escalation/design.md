# Design

## Context

En `main`, el flujo de `POST /api/chat` (`backend/app.py`) ejecuta:
1. `router_jeff.resolver_consulta()` -> canal `JEFF_ADMIN`.
2. Recuperación RAG (`rag_engine.buscar_fragmentos_relevantes`) + guard de cálculo directo + guard de fuera de foco (`fuera_de_foco` cuando no es saludo, no menciona tema del temario y `max_score < RAG_OFFTOPIC_SCORE`).
3. Si no cae en esos guards, invoca a Ollama (`TUTOR_SOCRATICO`), incluso cuando `contexto` está vacío o `max_score` está bajo el umbral mínimo.

Además, `frontend/src/services/api.ts` (`enviarMensajeChat`) solo reenvía eventos SSE de tipo `token` y descarta los metadatos de `inicio`/`fin`.

## Goals / Non-Goals

**Goals:**
- Evitar llamadas a Ollama cuando no exista respaldo real en Jeff ni en RAG (modo estricto configurable por ramo en `config.json`).
- Exponer metadatos SSE (`canal: "FALLBACK_DOCENTE"`, `puede_escalar: true`, `motivo`) para que el frontend muestre el botón de confirmación al estudiante.
- Persistir consultas escaladas por ramo en `consultas_profesor.json` y permitir al docente responderlas y convertirlas en entradas de `faqs_jeff` en `config.json`.

**Non-Goals:**
- Autenticación o identidad nominal del estudiante en el chat (las consultas se registran de forma anónima por ramo).
- Notificaciones por correo o mensajería externa al profesor fuera de la vista docente.

## Decisions

1. **Canal dedicado `FALLBACK_DOCENTE` en `/api/chat`**
   - *Decisión:* Unificar el fallback estricto bajo el canal SSE `FALLBACK_DOCENTE` cuando `config_fallback.habilitado` es verdadero y (a) `fuera_de_foco` es verdadero, o (b) no es saludo/resumen y `not bool(contexto)` (sin fragmentos por sobre `RAG_MIN_SCORE`).
   - *Alternativa considerada:* Mantener el guard actual en `TUTOR_SOCRATICO` sin escalamiento. Se descartó porque deja al estudiante sin salida cuando la pregunta es legítima pero falta material o FAQ.

2. **Persistencia separada en `consultas_profesor.json` por ramo**
   - *Decisión:* Guardar la configuración (`config_fallback`) en `backend/data/ramos/{CODIGO}/config.json` y los registros dinámicos de dudas en `backend/data/ramos/{CODIGO}/consultas_profesor.json` con lock de escritura.
   - *Alternativa considerada:* Guardar las consultas dentro de `config.json`. Se descartó para no mezclar metadatos estáticos/configuración del curso con datos transaccionales crecientes.

3. **Conversión directa a FAQ de Jeff (`faqs_jeff`)**
   - *Decisión:* Al responder una consulta en `POST /api/ramos/{codigo_ramo}/consultas/{id}/responder` con `guardar_en_jeff=true`, el backend agrega una entrada `{id, categoria, palabras_clave, respuesta}` a `faqs_jeff` en `config.json`. El frontend pre-sugiere `palabras_clave` filtrando palabras relevantes de la pregunta para que el docente solo las ajuste.
   - *Alternativa considerada:* Hacer que Jeff lea también `consultas_profesor.json`. Se descartó para mantener una sola fuente de verdad en `router_jeff.py` (`config.json`).

4. **Retrocompatibilidad del stream SSE en frontend**
   - *Decisión:* Ampliar `enviarMensajeChat` en `frontend/src/services/api.ts` con un callback opcional `onEvento` (o `onFin`) que entregue `canal`, `puede_escalar` y `motivo` sin romper el callback `onToken`.

## Risks / Trade-offs

- **[Falsos positivos en fallback estricto]** Si `RAG_MIN_SCORE` es muy alto, preguntas válidas podrían caer en fallback. → Mitigación: respetar la excepción de saludos y solicitudes de resumen del temario, y mantener configurable `config_fallback.habilitado` por ramo.
- **[Ruido en buzón docente]** Alumnos podrían enviar consultas poco claras. → Mitigación: exigir confirmación explícita con botón en el chat y permitir al profesor descartar consultas desde la vista docente.
- **[Concurrencia al escribir `config.json` / `consultas_profesor.json`]** Múltiples escrituras simultáneas podrían corromper JSON. → Mitigación: proteger lecturas/escrituras con un `threading.Lock` por archivo/ramo.
