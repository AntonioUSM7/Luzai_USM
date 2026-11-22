# Design

## Context

Ver `proposal.md` para la motivación. Actualmente `router_jeff.py` resuelve `faqs_jeff` y `tareas` desde `backend/data/ramos/<CODIGO>/config.json` mediante coincidencia determinista de `palabras_clave`. `consultas_store.py` persiste escalaciones y llama a `router_jeff.agregar_faq_jeff(...)` sin guardar el texto `pregunta`. Por su parte, `rag_engine.py` indexa únicamente documentos PDF/Markdown en ChromaDB (`luzai_<codigo>`), y `DocenteView.tsx` mantiene la sub-pestaña `jeff` como un placeholder.

## Goals / Non-Goals

**Goals:**
- Permitir que el docente administre (listar, buscar, crear, editar, eliminar) las preguntas guardadas (`faqs_jeff`) desde un apartado dedicado en `DocenteView.tsx`.
- Sincronizar cada pregunta guardada (`pregunta`, `categoria`, `respuesta`) con la colección ChromaDB del ramo (`rag_engine.py`) para que el Tutor Socrático la recupere semánticamente cuando Jeff no intercepte por palabras clave.
- Preservar la arquitectura de dos niveles (Opción A): Jeff a `$0 GPU` por palabras clave y Tutor Socrático con respaldo RAG.

**Non-Goals:**
- Reemplazar la coincidencia determinista de Jeff por embeddings o LLM.
- Editar o crear un CRUD separado para el arreglo `tareas` en esta iteración (aunque se mantiene intacto en `router_jeff.py`).
- Migrar `config.json` a una base de datos relacional.

## Decisions

### 1. Reutilizar `faqs_jeff` en `config.json` como fuente de verdad
- **Decisión**: Mantener `faqs_jeff` en `backend/data/ramos/<CODIGO>/config.json` agregando el campo opcional `pregunta: str`.
- **Alternativa considerada**: Crear un archivo JSON separado (`preguntas_jeff.json`). Se descartó porque `router_jeff.py` y las pruebas existentes (`test_jeff.py`, `test_fallback.py`) ya leen/escriben `faqs_jeff` en `config.json` bajo `_CONFIG_LOCK`.
- **Compatibilidad**: Entradas previas sin `pregunta` siguen funcionando en Jeff y se indexan en ChromaDB usando `categoria` + `respuesta` + `palabras_clave`.

### 2. Indexación en la misma colección ChromaDB con `carpeta="faqs_jeff"`
- **Decisión**: Guardar cada FAQ como un documento en la colección `luzai_<codigo>` de ChromaDB con ID determinista `faq_<faq_id>` y metadata `{"archivo": "Preguntas Guardadas (Jeff)", "carpeta": "faqs_jeff", "faq_id": faq_id, "categoria": categoria}`.
- **Texto indexado**: `Pregunta: <pregunta>\nCategoría: <categoria>\nRespuesta oficial: <respuesta>` (si no hay `pregunta`, usar `Palabras clave: ...`).
- **Por qué en la misma colección**: `rag_engine.buscar_fragmentos_relevantes(...)` ya consulta `luzai_<codigo>` sin filtrar por carpeta en `/api/chat`, por lo que las preguntas guardadas compiten naturalmente por similitud coseno junto con los apuntes y superan el umbral `MIN_SCORE` evitando falsos `sin_respaldo_rag`.
- **Ciclo de vida**:
  - `indexar_faq_jeff(codigo_ramo, faq)` hace `upsert` por ID `faq_<id>`.
  - `eliminar_faq_vectorial(codigo_ramo, faq_id)` elimina por ID `faq_<id>`.
  - `_reindexar_ramo(codigo_ramo)` lee `faqs_jeff` de `config.json` y las reindexa junto con los archivos del ramo.

### 3. Tolerancia a fallos de embeddings en operaciones CRUD
- **Decisión**: Si Ollama (`/api/embed`) no está disponible al guardar/editar una FAQ, la operación en `config.json` **no falla**: se registra un `warning` en logs y se retorna la FAQ guardada (con indicador opcional de sincronización o reindexación posterior).
- **Razón**: Evitar bloquear al docente cuando el servicio de embeddings está reiniciando o en tests unitarios sin Ollama activo.

### 4. Endpoints REST para Preguntas Guardadas
- `GET /api/ramos/{codigo_ramo}/faqs_jeff` — Lista `faqs_jeff` del ramo.
- `POST /api/ramos/{codigo_ramo}/faqs_jeff` — Crea una FAQ (`pregunta`, `respuesta`, `palabras_clave`, `categoria`) y sincroniza ChromaDB.
- `PUT /api/ramos/{codigo_ramo}/faqs_jeff/{faq_id}` — Actualiza una FAQ existente y re-indexa en ChromaDB.
- `DELETE /api/ramos/{codigo_ramo}/faqs_jeff/{faq_id}` — Elimina de `config.json` y de ChromaDB.
- Además, `consultas_store.responder_consulta(...)` pasa `pregunta=objetivo["pregunta"]` a `router_jeff.agregar_faq_jeff(...)` e indexa la FAQ resultante en `rag_engine`.

## Risks / Trade-offs

- **Desincronización si Ollama está caído al editar una FAQ** → Mitigación: `reindexar_ramo` incluye todas las `faqs_jeff`, permitiendo resincronizar en un clic desde la vista docente.
- **Formato de respuesta de Jeff con prefijo `📌 [Jeff - Respuesta Docente ...]` dentro del contexto RAG** → Mitigación: al construir el texto para ChromaDB o en el prompt del tutor, el contexto aparece claramente etiquetado como fuente oficial del docente (`Preguntas Guardadas (Jeff)`), y el tutor socrático sigue sus reglas pedagógicas al responder.
- **Duplicación de preguntas sin `palabras_clave` explícitas desde la UI** → Mitigación: si el docente deja `palabras_clave` vacío al crear una FAQ desde la UI teniendo `pregunta`, `router_jeff.agregar_faq_jeff` puede auto-sugerirlas con `sugerir_palabras_clave(pregunta)` (validando que quede al menos 1 keyword).
