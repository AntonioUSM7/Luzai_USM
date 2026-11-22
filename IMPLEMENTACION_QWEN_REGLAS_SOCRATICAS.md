# Implementación de Qwen3 8B + Reglas Socráticas Configurables — LuzAI USM

Este documento resume cómo quedó conectado el modelo generativo local **`qwen3:8b`** y la configuración pedagógica editable por el profesor desde la Vista Docente.

---

## 1. Flujo de datos

```text
DocenteView.tsx (Tab "Reglas Socraticas")
   - Estilo pedagogico: estricto | equilibrado | paso_a_paso
   - Extension: corta | media
   - Instrucciones del ramo (reglas_socraticas)
            |
            | PUT /api/ramos/{codigo_ramo}/config_socratica
            v
backend/app.py -> actualizar_config_socratica_ramo()
            |  (guardado atomico bajo router_jeff._CONFIG_LOCK)
            v
backend/data/ramos/{CODIGO}/config.json
            |
            v
POST /api/chat -> _construir_system_prompt() -> _eventos_ollama()
            |  payload: { model: "qwen3:8b", think: false, stream: true }
            v
Ollama (:11434) ---> Streaming SSE ---> ChatWindow.tsx
```

---

## 2. Referencia al código implementado

### Infraestructura / Entorno
- **[`docker-compose.yml`](docker-compose.yml)**:
  - `OLLAMA_LLM_MODEL=${OLLAMA_LLM_MODEL:-qwen3:8b}`
  - `OLLAMA_THINK=${OLLAMA_THINK:-false}` (desactiva la fase interna de pensamiento oculto de Qwen3 para iniciar el streaming inmediatamente).

### Configuración por ramo (`config.json`)
- **[`backend/data/ramos/MAT024/config.json`](backend/data/ramos/MAT024/config.json)** y **[`backend/data/ramos/TEL20425/config.json`](backend/data/ramos/TEL20425/config.json)**:
  ```json
  "config_socratica": {
    "estilo": "equilibrado",
    "extension": "media"
  }
  ```

### Backend
- **[`backend/app.py`](backend/app.py)**:
  - `OLLAMA_LLM_MODEL` (default `qwen3:8b`) y `OLLAMA_THINK` (default `False`).
  - `ConfigSocraticaReq`: valida `estilo` (`estricto` | `equilibrado` | `paso_a_paso`), `extension` (`corta` | `media`) y `reglas_socraticas`.
  - `_ESTILOS_SOCRATICOS`, `_EXTENSIONES_SOCRATICAS` y `_obtener_config_socratica()`: traducen las opciones del profesor a directivas concretas para el prompt.
  - `GET /api/ramos/{codigo_ramo}/config_socratica` y `PUT /api/ramos/{codigo_ramo}/config_socratica`: lectura y persistencia atómica en `config.json`.
  - `_construir_system_prompt()`: inyecta estilo, extensión y `reglas_socraticas` del ramo.
  - `_eventos_ollama()`: incluye `"think": OLLAMA_THINK` en el JSON enviado a Ollama.
- **[`backend/test_socratic_config.py`](backend/test_socratic_config.py)**:
  - Verifica envío de `model="qwen3:8b"` + `think=False`, construcción del prompt con estilo/extensión/reglas, persistencia de `GET`/`PUT` y rechazo `422` ante valores inválidos.

### Frontend
- **[`frontend/src/types.ts`](frontend/src/types.ts)**: `EstiloSocratico`, `ExtensionSocratica`, `ConfigSocratica`.
- **[`frontend/src/services/api.ts`](frontend/src/services/api.ts)**: `obtenerConfigSocratica()` y `actualizarConfigSocratica()`.
- **[`frontend/src/views/profesor/DocenteView.tsx`](frontend/src/views/profesor/DocenteView.tsx)**: pestaña **"Reglas Socráticas"** conectada al backend con tarjetas de estilo, selector de extensión, editor de instrucciones del ramo y guardado con notificación.

---

## 3. Nota para probar en vivo con `qwen3:8b`

Si el contenedor `luzai_smartguard_backend` ya estaba corriendo antes de editar `docker-compose.yml`, recréalo para que tome `OLLAMA_LLM_MODEL=qwen3:8b` y `OLLAMA_THINK=false`, y asegúrate de tener también el modelo de embeddings si vas a usar RAG:

```bash
docker compose up -d --force-recreate backend
ollama pull nomic-embed-text
```
