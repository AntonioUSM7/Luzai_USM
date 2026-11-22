# Implementación de Fallback Estricto y Escalamiento Docente (`FALLBACK_DOCENTE`) — LuzAI USM

Este documento describe la arquitectura, el flujo de datos y las referencias exactas al código de la capa **`FALLBACK_DOCENTE`**, implementada sobre `main` tras la integración de RAG y Jeff.

---

## 1. Arquitectura y flujo completo

```text
Alumno (ChatWindow.tsx)
        |
        | POST /api/chat { codigo_ramo, mensaje }
        v
FastAPI (backend/app.py -> chat())
        |
        +--> 1. Jeff (router_jeff.resolver_consulta)
        |       match en tareas / faqs_jeff -> SSE canal JEFF_ADMIN ($0 GPU)
        |
        +--> 2. RAG (rag_engine.buscar_fragmentos_relevantes)
        |       + guard de calculo directo (TUTOR_SOCRATICO)
        |
        +--> 3. Guard FALLBACK_DOCENTE ($0 GPU, sin llamar a Ollama)
        |       se activa si config_fallback.habilitado == true y:
        |         a) fuera_de_foco (no es saludo, no menciona temario, score < RAG_OFFTOPIC_SCORE)
        |         b) sin_respaldo_rag (no es saludo ni resumen y contexto esta vacio)
        |       -> SSE canal="FALLBACK_DOCENTE", puede_escalar=true, motivo="..."
        |
        +--> 4. Tutor Socratico (Ollama, canal TUTOR_SOCRATICO)
                solo si hay respaldo RAG (o es saludo/resumen)

Si cae en FALLBACK_DOCENTE:
Alumno pulsa "Enviar esta pregunta al profesor" (confirmacion explicita)
        |
        | POST /api/ramos/{codigo_ramo}/consultas
        v
consultas_store.crear_consulta() -> backend/data/ramos/{CODIGO}/consultas_profesor.json
        |
        v
Profesor (DocenteView.tsx -> pestana "Consultas de Alumnos")
        |
        | POST /api/ramos/{codigo_ramo}/consultas/{id}/responder
        | { estado: "resuelta", respuesta_profesor, guardar_en_jeff: true, palabras_clave }
        v
consultas_store.responder_consulta()
        |
        +--> router_jeff.agregar_faq_jeff() -> agrega FAQ en config.json
                                                    |
                                                    v
                 Siguiente alumno pregunta lo mismo -> JEFF_ADMIN ($0 GPU)
```

---

## 2. Configuración por ramo (`config.json`)

En [`backend/data/ramos/MAT024/config.json`](backend/data/ramos/MAT024/config.json) y [`backend/data/ramos/TEL20425/config.json`](backend/data/ramos/TEL20425/config.json) se agregó el bloque `config_fallback`:

```json
"config_fallback": {
  "habilitado": true,
  "permitir_escalar_profesor": true,
  "mensaje_sin_respaldo": "No encontré respaldo suficiente en los apuntes oficiales ni en la información administrativa de MAT024 para responder con certeza. Si quieres, puedes enviar esta pregunta al profesor para que la revise.",
  "mensaje_fuera_de_foco": "Esa consulta parece estar fuera del foco de MAT024. Este tutor responde únicamente con base en los contenidos oficiales del curso. Si crees que sí está relacionada con la asignatura, puedes enviarla al profesor.",
  "canal_alternativo": "Foro de consultas en AULA USM"
}
```

Si un ramo nuevo no incluye `config_fallback`, `_obtener_config_fallback()` en `backend/app.py` aplica valores por defecto seguros (`habilitado=True`, `permitir_escalar_profesor=True`).

---

## 3. Referencia al código implementado

### Backend

1. **[`backend/app.py`](backend/app.py)**
   - `_respuesta_fija(...)`: acepta `canal` (por defecto `"TUTOR_SOCRATICO"`) y propaga `**extra` (`puede_escalar`, `motivo`, `fuera_de_foco`) tanto en el evento SSE `inicio` como en `fin`.
   - `_obtener_config_fallback(datos_ramo, codigo)`: carga `config_fallback` con defaults.
   - `POST /api/chat` (`chat()`): evalúa `fuera_de_foco` y `sin_respaldo_rag` antes de invocar a `_eventos_ollama()`. Cuando cualquiera se cumple y el modo estricto está activo, responde por SSE con `canal: "FALLBACK_DOCENTE"` sin consumir GPU.
   - Endpoints del buzón docente:
     - `GET /api/ramos/{codigo_ramo}/consultas` (`listar_consultas_profesor`): lista consultas del ramo (filtrable por `estado`).
     - `POST /api/ramos/{codigo_ramo}/consultas` (`crear_consulta_profesor`): registra la pregunta confirmada por el estudiante.
     - `POST /api/ramos/{codigo_ramo}/consultas/{consulta_id}/responder` (`responder_consulta_profesor`): marca la consulta como `resuelta` o `descartada`, y si `guardar_en_jeff=true`, crea la FAQ en `config.json`.

2. **[`backend/consultas_store.py`](backend/consultas_store.py)**
   - Persistencia thread-safe y atómica (`_STORE_LOCK` + archivo temporal + `os.replace`) en `backend/data/ramos/{CODIGO}/consultas_profesor.json`.
   - `crear_consulta(...)`: genera `id`, timestamp, estado `"pendiente"` y `palabras_clave_sugeridas` usando `router_jeff.sugerir_palabras_clave()`.
   - `listar_consultas(...)`: devuelve las consultas más recientes primero.
   - `responder_consulta(...)`: actualiza estado/respuesta y delega en `router_jeff.agregar_faq_jeff()` cuando corresponde.

3. **[`backend/router_jeff.py`](backend/router_jeff.py)**
   - `sugerir_palabras_clave(pregunta)`: normaliza y extrae palabras candidatas (>= 4 caracteres, filtrando stopwords en español) para pre-llenar las keywords en la vista docente.
   - `agregar_faq_jeff(...)`: agrega atómicamente una nueva entrada `{id, categoria, palabras_clave, respuesta}` a `faqs_jeff` dentro de `config.json` bajo `_CONFIG_LOCK`.

4. **[`backend/test_fallback.py`](backend/test_fallback.py)**
   - `TestFallbackEstricto`: verifica que consultas fuera de foco o sin respaldo RAG emitan `FALLBACK_DOCENTE` con `puede_escalar=True` y **nunca** invoquen `_eventos_ollama`.
   - `TestBuzonDocenteYConversionJeff`: verifica el ciclo completo crear -> listar -> responder con `guardar_en_jeff=True` -> preservación de `config.json` -> match inmediato en `router_jeff.resolver_consulta` y `/api/chat` por `JEFF_ADMIN`; y verifica que descartar no modifica `faqs_jeff`.

### Frontend

1. **[`frontend/src/types.ts`](frontend/src/types.ts)**
   - Nuevos tipos `CanalChat`, `EventoMetadataChat` y `ConsultaProfesor`.
   - Extensión de `MensajeChat` con `canal`, `puedeEscalar`, `motivoFallback`, `preguntaOriginal` y `estadoEscalamiento`.

2. **[`frontend/src/services/api.ts`](frontend/src/services/api.ts)**
   - `enviarMensajeChat(..., onMetadata?)`: procesa eventos SSE `inicio` y `fin` además de `token`.
   - `enviarConsultaProfesor(...)`, `listarConsultasProfesor(...)` y `responderConsultaProfesor(...)`.

3. **[`frontend/src/views/alumno/ChatWindow.tsx`](frontend/src/views/alumno/ChatWindow.tsx)**
   - Captura metadatos SSE en cada mensaje del asistente.
   - Si `canal === 'FALLBACK_DOCENTE'` y `puedeEscalar === true`, renderiza el botón **"Enviar esta pregunta al profesor"**; tras confirmar, llama a `enviarConsultaProfesor` y cambia a estado *"Consulta enviada al profesor"*.

4. **[`frontend/src/views/profesor/DocenteView.tsx`](frontend/src/views/profesor/DocenteView.tsx)**
   - Nueva pestaña **"Consultas de Alumnos"** con contador de pendientes y filtros (`pendientes`, `resueltas`, `descartadas`, `todas`).
   - Formulario por consulta pendiente con textarea de respuesta, checkbox **"Guardar como FAQ de Jeff"**, campos editables de **Palabras clave** (pre-cargadas desde `palabras_clave_sugeridas`) y **Categoría**, y botones **"Responder y guardar en Jeff"** / **"Descartar"**.

---

## 4. Comandos de verificación

```bash
# Pruebas de backend (en el contenedor)
docker exec luzai_smartguard_backend python3 /app/test_fallback.py -v
docker exec luzai_smartguard_backend python3 /app/test_jeff.py
docker exec luzai_smartguard_backend python3 /app/test_modo.py

# Verificación de tipos y build de frontend (en el contenedor)
docker exec luzai_smartguard_frontend sh -c "npx tsc --noEmit && npm run build"
```
