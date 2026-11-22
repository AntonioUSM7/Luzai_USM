# Design

## Context

En `backend/app.py`:
- `_construir_system_prompt()` lee `reglas_socraticas` de `config.json`, pero no contempla parámetros estructurados de estilo ni extensión.
- `_eventos_ollama()` llama a `${OLLAMA_HOST}/api/chat` con `OLLAMA_LLM_MODEL` (`qwen2.5:3b` por defecto en `docker-compose.yml`), sin enviar el parámetro `think` que en `qwen3:8b` evita la fase inicial de razonamiento interno oculto.
- En `frontend/src/views/profesor/DocenteView.tsx`, la pestaña `"Reglas Socráticas"` (`subTab === 'socratico'`) muestra únicamente texto informativo sin controles ni persistencia.

## Goals / Non-Goals

**Goals:**
- Conectar `qwen3:8b` como modelo por defecto con `think: false` configurable mediante `OLLAMA_THINK`.
- Permitir al docente configurar `reglas_socraticas`, `estilo` y `extension` por ramo desde `DocenteView.tsx`, persistiendo en `config.json`.
- Traducir `estilo` y `extension` a directivas concretas dentro de `_construir_system_prompt()`.

**Non-Goals:**
- Exponer parámetros avanzados de inferencia por ramo (`temperature`, `top_k`, `num_ctx`) en esta primera iteración (queda para una fase posterior).

## Decisions

1. **Esquema `config_socratica` en `config.json`**
   - *Decisión:* Agregar `"config_socratica": { "estilo": "equilibrado", "extension": "media" }` junto al campo existente `"reglas_socraticas"` en `config.json`, usando valores por defecto seguros si el bloque no existe.
   - *Alternativa considerada:* Guardar en un archivo separado. Se descartó porque `reglas_socraticas` ya vive en `config.json` y el volumen de datos es pequeño y estático.

2. **Validación estricta con Pydantic + escritura atómica**
   - *Decisión:* Usar `Literal["estricto", "equilibrado", "paso_a_paso"]` y `Literal["corta", "media"]` en FastAPI, y escribir `config.json` con `threading.Lock` + archivo temporal + `os.replace` para evitar corrupción concurrente con `router_jeff.agregar_faq_jeff`.

3. **Control de `think` vía variable de entorno `OLLAMA_THINK`**
   - *Decisión:* Leer `OLLAMA_THINK = os.getenv("OLLAMA_THINK", "false").lower() in ("1", "true", "yes")` en `backend/app.py` e incluir `"think": OLLAMA_THINK` en el payload de `/api/chat` hacia Ollama.
   - *Alternativa considerada:* Omitir `think` y depender de `/no_think` en el prompt. Se descartó porque el campo nativo `"think": false` de la API de Ollama es explícito y no ensucia el prompt.

## Risks / Trade-offs

- **[Consumo de VRAM con `qwen3:8b`]** `qwen3:8b` en Q4_K_M ocupa ~5.2 GB. → Mitigación: mantener `OLLAMA_NUM_CTX=4096` u `8192` en `docker-compose.yml` y `temperature: 0.2`.
- **[Falta de `nomic-embed-text` en Ollama local]** Si solo está `qwen3:8b`, el RAG no podrá generar embeddings hasta ejecutar `ollama pull nomic-embed-text`. → Mitigación: documentar/verificar ambos modelos en el arranque.
