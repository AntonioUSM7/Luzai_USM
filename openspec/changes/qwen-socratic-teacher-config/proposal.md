# Proposal

## Why

Actualmente el backend apunta por defecto a `qwen2.5:3b` en `docker-compose.yml` sin desactivar el modo `thinking` de modelos `qwen3` (como `qwen3:8b` disponible localmente), y las reglas socráticas por ramo (`reglas_socraticas` en `config.json`) solo pueden editarse manualmente en disco porque la pestaña **"Reglas Socráticas"** de `DocenteView.tsx` es un placeholder estático. Necesitamos conectar `qwen3:8b` optimizado para streaming inmediato y permitir que el profesor configure el comportamiento socrático de su ramo desde la interfaz docente.

## What Changes

- Configurar `qwen3:8b` como modelo LLM por defecto en `docker-compose.yml` y `backend/app.py`, agregando control de `think` (`OLLAMA_THINK=false` por defecto) en el payload hacia Ollama (`/api/chat`) para evitar latencia inicial en respuestas demostrativas.
- Agregar bloque `config_socratica` (`estilo`: `estricto` | `equilibrado` | `paso_a_paso`, `extension`: `corta` | `media`) en `config.json` por ramo y reflejarlo en `_construir_system_prompt()` de `backend/app.py`.
- Exponer endpoints `GET /api/ramos/{codigo_ramo}/config_socratica` y `PUT /api/ramos/{codigo_ramo}/config_socratica` en `backend/app.py` con persistencia atómica en `config.json`.
- Conectar la pestaña **"Reglas Socráticas"** en `frontend/src/views/profesor/DocenteView.tsx` (y helpers en `frontend/src/services/api.ts` y `frontend/src/types.ts`) para editar y guardar `reglas_socraticas`, `estilo` y `extension` por ramo.

## Capabilities

### New Capabilities
- `socratic-tutor-config`: Permite configurar por asignatura las reglas socráticas, el estilo pedagógico y la extensión de respuesta desde la vista docente, inyectándolos en el prompt del modelo generativo local (`qwen3:8b`).

### Modified Capabilities
<!-- Ninguna capacidad existente cambia a nivel de contrato de especificación -->

## Impact

- **Infra / Entorno:** `docker-compose.yml` (`OLLAMA_LLM_MODEL=qwen3:8b`, `OLLAMA_THINK=false`).
- **Backend:** `backend/app.py` (`_construir_system_prompt`, `_eventos_ollama`, nuevos endpoints `/api/ramos/{codigo_ramo}/config_socratica`), `backend/data/ramos/*/config.json`, y pruebas unitarias en `backend/test_socratic_config.py`.
- **Frontend:** `frontend/src/types.ts`, `frontend/src/services/api.ts`, `frontend/src/views/profesor/DocenteView.tsx`.
