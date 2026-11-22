# Proposal

## Why

Actualmente las preguntas guardadas para Jeff (`faqs_jeff` en `config.json`) solo almacenan `palabras_clave` y `respuesta` (sin la pregunta original), no cuentan con un apartado de gestión en la vista docente (la pestaña `jeff` es un placeholder), y son invisibles para el Tutor Socrático (Qwen3 8B + RAG). Si un estudiante formula una pregunta ya resuelta usando palabras distintas a las keywords exactas o hace una repregunta conceptual, el RAG solo busca en los apuntes PDF y puede caer en fallback (`sin_respaldo_rag`) ignorando la respuesta oficial del docente.

## What Changes

- **Modelo y persistencia de preguntas guardadas**: extender las entradas de `faqs_jeff` en `backend/data/ramos/<CODIGO>/config.json` para incluir opcionalmente `pregunta` (texto de referencia de la pregunta guardada), manteniendo compatibilidad con las FAQs existentes. Al responder una consulta escalada con `guardar_en_jeff=true`, guardar también la `pregunta` original.
- **API CRUD de preguntas guardadas de Jeff**: exponer endpoints en `backend/app.py` para listar, crear, editar y eliminar entradas de `faqs_jeff` por ramo (reutilizando bloqueo atómico en `router_jeff.py`).
- **Búsqueda dual (Opción A: Jeff + Tutor Socrático vía RAG)**:
  - **Jeff (`router_jeff.py`)**: mantiene la interceptación determinista a `$0 GPU` por `palabras_clave` sobre `tareas` y `faqs_jeff`.
  - **Tutor Socrático (`rag_engine.py`)**: indexar cada pregunta guardada (`pregunta` + `respuesta` + `categoria`) en la colección ChromaDB del ramo (por ejemplo con `carpeta="faqs_jeff"` y `faq_id`), actualizar/eliminar el vector al editar o borrar la entrada, e incluirlas en `reindexar_ramo`. De este modo, si Jeff no intercepta por keywords, el RAG recupera la pregunta guardada por similitud semántica y la entrega como contexto oficial al Tutor Socrático (evitando fallbacks falsos).
- **Apartado de Preguntas Guardadas en Vista Docente**: reemplazar el placeholder de la sub-pestaña `jeff` en `frontend/src/views/profesor/DocenteView.tsx` por un panel completo para buscar, crear, editar y eliminar preguntas guardadas (pregunta, respuesta, categoría y palabras clave).

## Capabilities

### New Capabilities
- `saved-questions-knowledge-base`: Gestión docente (CRUD API y panel UI en la pestaña Jeff) e indexación vectorial en ChromaDB de preguntas y respuestas guardadas para que el Tutor Socrático las recupere semánticamente como respaldo oficial del curso.

### Modified Capabilities
- `semantic-router`: Las entradas de `faqs_jeff` soportan el campo `pregunta` y su ciclo de vida CRUD, manteniendo la interceptación determinista a `$0 GPU` en Jeff y alimentando la recuperación semántica del tutor cuando no hay coincidencia exacta de palabras clave.

## Impact

- **Backend**: `backend/router_jeff.py`, `backend/consultas_store.py`, `backend/rag_engine.py`, `backend/app.py` y pruebas unitarias/integración (`backend/test_jeff.py`, `backend/test_rag.py`, `backend/test_fallback.py`).
- **Frontend**: `frontend/src/types.ts`, `frontend/src/services/api.ts`, `frontend/src/views/profesor/DocenteView.tsx`.
- **Datos**: `backend/data/ramos/<CODIGO>/config.json` (campo opcional `pregunta` en `faqs_jeff`) y colección ChromaDB por ramo (`backend/data/ramos/<CODIGO>/chroma`).
