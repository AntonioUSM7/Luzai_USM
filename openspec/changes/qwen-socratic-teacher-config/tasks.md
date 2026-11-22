# Tasks

## 1. Conexión a Qwen3 8B y soporte de `config_socratica` en backend

- [x] 1.1 Actualizar `docker-compose.yml` y `backend/app.py` para usar `qwen3:8b` como modelo por defecto (`OLLAMA_LLM_MODEL`), agregar `OLLAMA_THINK=false` por defecto e incluir `"think": OLLAMA_THINK` en el payload de `_eventos_ollama()`, verificando con pruebas unitarias en `backend/test_socratic_config.py`.
- [x] 1.2 Agregar el bloque `config_socratica` (`estilo`: `equilibrado`, `extension`: `media`) en `backend/data/ramos/MAT024/config.json` y `backend/data/ramos/TEL20425/config.json`, y actualizar `_construir_system_prompt()` en `backend/app.py` para aplicar `estilo`, `extension` y `reglas_socraticas`, verificando el contenido del prompt generado en `backend/test_socratic_config.py`.

## 2. Endpoints de configuración socrática por ramo

- [x] 2.1 Implementar en `backend/app.py` los endpoints `GET /api/ramos/{codigo_ramo}/config_socratica` y `PUT /api/ramos/{codigo_ramo}/config_socratica` con validación Pydantic (`estricto` | `equilibrado` | `paso_a_paso` y `corta` | `media`) y guardado atómico en `config.json`, verificando persistencia y rechazo de valores inválidos en `backend/test_socratic_config.py`.

## 3. Interfaz Docente para "Reglas Socráticas" y verificación

- [x] 3.1 Extender `frontend/src/types.ts` y `frontend/src/services/api.ts` con el tipo `ConfigSocratica` y las funciones `obtenerConfigSocratica` y `actualizarConfigSocratica`, verificando compilación TypeScript con `npx tsc --noEmit`.
- [x] 3.2 Reemplazar el placeholder de la pestaña **"Reglas Socráticas"** en `frontend/src/views/profesor/DocenteView.tsx` por un formulario editable (selector de estilo, selector de extensión, textarea de `reglas_socraticas` y botón de guardado con feedback), verificando con `npx tsc --noEmit && npm run build`.
- [x] 3.3 Ejecutar `backend/test_socratic_config.py` junto a `test_fallback.py`, `test_jeff.py`, `test_modo.py` y `npm run build` en los contenedores, confirmando que todo pasa sin errores.
