# Implementación RAG + Jeff + Markdown/LaTeX — LuzAI USM

- **Proyecto:** LuzAI USM (Tutor Socrático Institucional)
- **Rama:** `RAG_development`
- **Responsable:** Ahmaru (técnico)
- **Fecha de cierre de esta bitácora:** 15-11-2026
- **Alcance:** motor RAG, enrutador administrativo Jeff, integración FastAPI, ajustes de entorno Docker/SELinux/Ollama y renderizado Markdown + LaTeX en el chat del frontend.

Este documento resume **todo lo implementado**, los archivos tocados, las decisiones técnicas, los comandos de ejecución/verificación y los resultados obtenidos.

---

## 1. Resumen ejecutivo

Se dejó operativo el flujo completo del tutor:

1. El alumno escribe en el chat React (`frontend`).
2. El backend FastAPI intenta primero resolver la consulta con **Jeff** (administrativo, determinista, sin GPU).
3. Si no es administrativa, el backend recupera contexto de los apuntes con **RAG** (`nomic-embed-text` + ChromaDB).
4. El contexto se inyecta en un **LLM socrático** servido por Ollama (`qwen2.5:3b` por defecto).
5. La respuesta se transmite por **SSE** y el frontend la renderiza con **Markdown + GFM + LaTeX (KaTeX)**.

Resultados principales:

- 16 PDFs de MAT024 indexados en **800 fragmentos** vectoriales.
- Búsqueda semántica funcional con puntajes relevantes (~0.71 en la consulta de prueba).
- Indexación idempotente, borrado de vectores por archivo/carpeta y reindexación completa.
- Subida de PDF indexada en segundo plano (800 → 940 fragmentos, luego de vuelta a 800 al borrar).
- Jeff resuelve dudas administrativas sin consumir GPU.
- Chat con streaming SSE y contexto RAG verificado.
- Frontend compila con TypeScript y Vite; renderiza encabezados, listas, tablas, código, imágenes y fórmulas LaTeX.
- El prompt del tutor fue reforzado para exigir Markdown y delimitadores `$...$` / `$$...$$`.

---

## 2. Arquitectura y flujo

```text
Alumno (React + Vite :5173)
        |
        | POST /api/chat  { codigo_ramo, mensaje }
        v
FastAPI (:8000)
        |
        +--> 1. Jeff (router_jeff.py)
        |       normaliza texto, busca keywords en config.json
        |       si hay match -> SSE canal JEFF_ADMIN (sin GPU)
        |
        +--> 2. RAG (rag_engine.py)
        |       embedding de la consulta (nomic-embed-text)
        |       ChromaDB persistente por ramo -> top-k fragmentos
        |       formatea contexto con fuentes y páginas
        |
        +--> 3. Ollama (/api/chat, qwen2.5:3b)
                system prompt socrático + contexto
                streaming de tokens -> SSE canal TUTOR_SOCRATICO

Frontend
        |
        +--> ReactMarkdown + remark-gfm + remark-math + rehype-katex
                imágenes/enlaces /api/... resueltos contra API_URL
```

### Formato SSE

Cada evento se envía como:

```text
data: {"tipo":"token","contenido":"..."}\n\n
```

Eventos especiales:

- `{"tipo":"inicio","canal":"TUTOR_SOCRATICO","con_contexto":true|false}`
- `{"tipo":"fin","canal":"JEFF_ADMIN","topico":"...","categoria":"..."}`
- `{"tipo":"fin","canal":"TUTOR_SOCRATICO"}`

---

## 3. Fases implementadas

### 3.1 Diagnóstico inicial

- Los apuntes son PDFs basados en diapositivas.
- La extracción de texto funciona, pero **no hay marcadores LaTeX `$...$` en el PDF original** (0 encontrados): muchas fórmulas están como imagen o texto plano.
- Se extraen imágenes de los PDFs y se sirven por API.
- `pymupdf4llm` advierte que `RapidOCR` no está instalado; solo afecta a PDFs escaneados.

### 3.2 Motor RAG (`backend/rag_engine.py`)

Reescritura completa del motor con estas capacidades:

- **Extracción:** `pymupdf4llm.to_markdown(..., page_chunks=True, write_images=True, image_format="png")`.
- **Imágenes:** se guardan en `backend/data/ramos/<RAMO>/imagenes/<stem_pdf>/` y se reescriben como rutas `/api/ramos/<RAMO>/imagenes/...`.
- **Chunking semántico Markdown:**
  - Respeta encabezados, párrafos y bloques de código.
  - `RAG_CHUNK_SIZE=700`, `RAG_CHUNK_OVERLAP=100` por defecto.
  - Parte bloques demasiado largos con solapamiento.
- **Embeddings:**
  - Modelo `nomic-embed-text` vía Ollama.
  - Lote por `/api/embed` con `RAG_EMBEDDING_BATCH_SIZE=32`.
  - Fallback automático a `/api/embeddings` por fragmento si el lote falla.
  - Prefijos `search_document:` / `search_query:` controlados por `RAG_EMBEDDING_PREFIXES=1`.
- **ChromaDB:**
  - `PersistentClient` por ramo en `data/ramos/<RAMO>/chroma`.
  - Colección `luzai_<ramo>` con distancia coseno.
  - Metadatos por fragmento: `archivo`, `carpeta`, `pagina`, `codigo_ramo`.
- **Idempotencia:** antes de indexar un archivo se eliminan sus vectores previos; reindexar no duplica.
- **Borrado:** por archivo, por archivo+carpeta, por carpeta y por ramo completo.
- **Concurrencia:** locks `RLock` para escritura y caché de clientes Chroma.
- **Funciones expuestas al backend:**
  - `indexar_documento(ruta, codigo, carpeta)`
  - `reindexar_ramo(codigo)`
  - `eliminar_documento_vectorial(...)`
  - `eliminar_carpeta_vectorial(...)`
  - `esta_indexado(...)`
  - `buscar_fragmentos(...)`
  - `buscar_contexto_relevante(...)`
  - `formatear_contexto(...)`
  - `obtener_cliente_chroma(...)`

### 3.3 Enrutador Jeff (`backend/router_jeff.py`)

Implementación determinista y sin GPU:

- `normalizar()`: minúsculas, sin tildes (NFKD), espacios colapsados.
- `_coincide()`: coincidencia por límite de palabra para keywords de una palabra; subcadena para frases.
- `_puntuar()`: suma longitudes de keywords coincidentes; ignora claves de menos de 3 caracteres.
- Prioridad: primero `tareas`, luego `faqs_jeff`.
- Salida: `canal`, `tipo`, `topico`, `categoria`, `respuesta`, `coincidencias`, `puntaje`.
- Si no hay coincidencia devuelve `None` y el backend deriva a RAG + LLM.
- Formato de tareas: título, fecha límite, formato de entrega y plataforma (o respuesta explícita si existe).

### 3.4 Integración API (`backend/app.py`)

- **Subida de archivos:** guarda el PDF y agenda `rag_engine.indexar_documento` con `BackgroundTasks`.
- **Listado de archivos:** incluye `indexado_rag` consultando Chroma.
- **Borrado de archivo:** elimina el PDF y sus vectores.
- **Borrado de carpeta:** elimina recursivamente y limpia vectores por carpeta.
- **Reindexación:** `POST /api/ramos/{codigo}/reindexar` reconstruye la colección en segundo plano.
- **Estado RAG:** `GET /api/ramos/{codigo}/estado_rag` devuelve `fragmentos_indexados`.
- **Imágenes:** `GET /api/ramos/{codigo}/imagenes/{ruta:path}` con validación anti path traversal.
- **Chat:** flujo `Jeff -> RAG -> Ollama` con `StreamingResponse` y SSE.
- **Prompt socrático:** incluye reglas del ramo, contexto oficial y una sección final de **formato obligatorio Markdown + LaTeX**.
- **LLM configurable:** `OLLAMA_LLM_MODEL` (default `qwen2.5:3b`), `temperature=0.3`.

### 3.5 Frontend Markdown + LaTeX

Dependencias agregadas a `frontend/package.json`:

- `react-markdown@10.1.0`
- `remark-gfm@4.0.1`
- `remark-math@6.0.0`
- `rehype-katex@7.0.1`
- `katex@0.19.1`

Cambios realizados:

1. **`frontend/src/main.tsx`**
   - Importa `katex/dist/katex.min.css` después de `index.css`.

2. **`frontend/src/services/api.ts`**
   - `API_URL` ahora es exportado.
   - Nuevo helper `resolverUrlApi(url)`:
     - Si la URL empieza con `/api/`, la prefija con `API_URL`.
     - Si es absoluta (`http://`, `https://`, `data:`), la deja igual.

3. **`frontend/src/views/alumno/ChatWindow.tsx`**
   - Importa `ReactMarkdown`, `remark-gfm`, `remark-math`, `rehype-katex`.
   - Define `componentesMarkdown`:
     - `img`: resuelve `src` con `resolverUrlApi`, agrega `loading="lazy"`.
     - `a`: resuelve `href`, abre en pestaña nueva con `rel="noopener noreferrer"`.
   - Los mensajes del **asistente** se renderizan dentro de `<div className="markdown-content">` con:
     - `remarkPlugins={[remarkGfm, remarkMath]}`
     - `rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}`
   - Los mensajes del **usuario** conservan `<p className="whitespace-pre-wrap">`.
   - `throwOnError: false` evita que una fórmula incompleta durante el streaming rompa el chat.

4. **`frontend/src/index.css`**
   - Estilos `.markdown-content` para encabezados, párrafos, listas, código, bloques de código, blockquote, tablas, enlaces, imágenes y `.katex-display` con scroll horizontal.

5. **Prompt del backend (`_construir_system_prompt`)**
   - Instrucción obligatoria de Markdown (encabezados `##`, listas, negritas, tablas, bloques de código).
   - LaTeX inline `$...$` y desplegado `$$...$$` para toda variable/expresión.
   - Prohibición de `\(...\)` y `\[...\]` (no soportados por `remark-math` por defecto).
   - Ejemplo de estilo y prohibición de HTML crudo.

### 3.6 Seguridad del renderizado

- `react-markdown` **no interpreta HTML crudo** por defecto.
- Enlaces externos con `target="_blank"` y `rel="noopener noreferrer"`.
- Imágenes servidas por endpoint con validación `relative_to(base)` para evitar path traversal.
- El frontend no ejecuta scripts embebidos en las respuestas del LLM.

---

## 4. Endpoints del backend

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado, modelo LLM, modelo de embeddings y `OLLAMA_HOST`. |
| GET | `/api/ramos` | Lista de ramos con su configuración. |
| GET | `/api/ramos/{codigo}/carpetas` | Lista carpetas de documentos. |
| POST | `/api/ramos/{codigo}/carpetas` | Crea carpeta. Body: `{"nombre":"..."}`. |
| GET | `/api/ramos/{codigo}/archivos` | Lista archivos con `indexado_rag`. |
| POST | `/api/ramos/{codigo}/archivos` | Sube PDF (multipart: `archivo`, `carpeta`) e indexa en background. |
| DELETE | `/api/ramos/{codigo}/archivos?carpeta=...&nombre_archivo=...` | Elimina archivo y sus vectores. |
| DELETE | `/api/ramos/{codigo}/carpetas?nombre_carpeta=...` | Elimina carpeta, archivos y vectores. |
| POST | `/api/ramos/{codigo}/reindexar` | Reconstruye la base vectorial en background. |
| GET | `/api/ramos/{codigo}/estado_rag` | Devuelve `fragmentos_indexados`. |
| GET | `/api/ramos/{codigo}/imagenes/{ruta:path}` | Sirve imágenes extraídas de PDFs. |
| POST | `/api/chat` | Chat SSE. Body: `{"codigo_ramo":"MAT024","mensaje":"..."}`. |

Documentación interactiva: `http://localhost:8000/docs`.

---

## 5. Variables de entorno

### Backend

| Variable | Default | Uso |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` (código) / `http://host.docker.internal:11434` (Compose) | URL de Ollama. |
| `OLLAMA_LLM_MODEL` | `qwen2.5:3b` | Modelo del tutor socrático. |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Modelo de embeddings. |
| `RAG_CHUNK_SIZE` | `700` | Tamaño máximo de fragmento (caracteres). |
| `RAG_CHUNK_OVERLAP` | `100` | Solapamiento entre fragmentos. |
| `RAG_TOP_K` | `4` | Fragmentos recuperados por consulta. |
| `RAG_EMBEDDING_BATCH_SIZE` | `32` | Textos por lote de embeddings. |
| `RAG_EMBEDDING_PREFIXES` | `1` | Usa prefijos `search_document:` / `search_query:`. |
| `RAG_MIN_SCORE` | `0.25` | Descarta fragmentos con similitud menor al umbral. |
| `RAG_OFFTOPIC_SCORE` | `0.65` | Score mínimo para considerar una consulta dentro del ramo cuando no hay palabra clave del temario. |
| `RAG_AUTO_REINDEX` | `1` | Reindexa al arrancar los ramos que tengan documentos sin indexar (modo temporal de prueba). |
| `OLLAMA_NUM_CTX` | `8192` | Ventana de contexto del LLM; evita que se trunquen el contexto y las reglas del prompt. |
| `HOME` | `/tmp` (Compose) | Evita problemas de permisos de Chroma. |
| `ANONYMIZED_TELEMETRY` | `False` (Compose) | Desactiva telemetría de Chroma. |
| `CHROMA_TELEMETRY_ENABLED` | `False` (Compose) | Desactiva telemetría de Chroma. |

### Frontend

| Variable | Default | Uso |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | URL base del backend. |

---

## 6. Persistencia y estructura de datos

```text
backend/data/ramos/MAT024/
├── config.json                 # nombre, reglas, tareas, faqs_jeff
├── documentos/
│   ├── Clases/*.pdf
│   ├── Tareas/*.pdf
│   ├── Guias/*.pdf
│   ├── Certamenes/*.pdf
│   └── General/*.pdf
├── imagenes/
│   └── <nombre_pdf>/*.png      # imágenes extraídas por pymupdf4llm
└── chroma/                     # PersistentClient de ChromaDB
```

Configuración actual de los ramos:

- `MAT024`: 3 FAQs Jeff + 1 tarea.
- `TEL20425`: 3 FAQs Jeff + 1 tarea.

Los vectores se identifican como:

```text
<carpeta>__<archivo>__p<pagina>__c<indice_chunk>
```

---

## 7. Ajustes de entorno (Docker, SELinux y Ollama)

Problemas encontrados y soluciones aplicadas:

1. **SELinux en modo Enforcing**
   - Los bind mounts fallaban con permisos.
   - Solución: volúmenes con sufijo `:z`:
     - `./backend:/app:z`
     - `./frontend:/app:z`

2. **Permisos de ChromaDB dentro del contenedor**
   - Solución: backend con `user: "${UID:-1000}:${GID:-1000}"`, `HOME=/tmp` y telemetría desactivada.

3. **Contexto de build demasiado grande**
   - Se agregaron `backend/.dockerignore` y `frontend/.dockerignore` para excluir `data/`, `node_modules`, `dist`, etc.

4. **Ollama accesible desde Docker**
   - Ollama se configuró para escuchar en `0.0.0.0:11434` mediante override de systemd.
   - Compose usa `host.docker.internal:11434` y `extra_hosts: host.docker.internal:host-gateway`.

5. **Usuario sin grupo Docker en la sesión**
   - El usuario `knsyx` fue agregado al grupo `docker` (GID 967).
   - Si la sesión actual no tiene el grupo, usar:
     ```bash
     sg docker -c "docker ps"
     ```

6. **`frontend/node_modules` root-owned**
   - Se eliminó el directorio vacío con `rmdir frontend/node_modules`.
   - Se instalaron dependencias localmente con `npm install`.
   - El contenedor se recreó renovando el volumen anónimo:
     ```bash
     sg docker -c "docker compose up -d --build --force-recreate -V frontend"
     ```

7. **Versión de ChromaDB**
   - Entorno actual: `chromadb 1.5.9`.
   - Si otra versión de Chroma no puede abrir la base local, borrar `backend/data/ramos/MAT024/chroma` o llamar a `/api/ramos/MAT024/reindexar`.

---

## 8. Pruebas y resultados

### 8.1 Motor RAG

```bash
docker compose exec backend python test_rag.py --solo-buscar --query "¿Cómo se calcula una integral de superficie?"
```

Resultados registrados:

- 16 PDFs de MAT024 indexados en **800 fragmentos**.
- Consulta de prueba recuperó páginas **11, 6 y 3** con scores cercanos a **0.71**.
- Reindexar un archivo existente mantuvo **20 chunks** (sin duplicar).
- Subida de `Test_Upload.pdf`: **800 → 940** fragmentos en ~20 s.
- Borrado del archivo de prueba: **940 → 800** fragmentos.
- Reindexación completa del ramo funcional.

### 8.2 Enrutador Jeff

```bash
docker compose exec backend python test_jeff.py
```

Casos verificados:

- “¿Cuándo es el certamen de MAT024?” → `JEFF_ADMIN`.
- “¿Qué libro recomienda el ramo?” → `JEFF_ADMIN`.
- “¿Cómo se entrega la tarea 1?” → `JEFF_ADMIN`.
- “¿Dónde es el laboratorio de TEL20425?” → `JEFF_ADMIN`.
- “¿Cómo parametrizo la frontera de la semiesfera?” → `TUTOR_SOCRATICO` (deriva a RAG).
- “ensalada de frutas” → `TUTOR_SOCRATICO` (deriva a RAG).

### 8.3 Chat con streaming

- Consulta administrativa: canal `JEFF_ADMIN`, sin llamada al LLM.
- Consulta conceptual: canal `TUTOR_SOCRATICO`, `con_contexto=true`, ~504 eventos SSE.
- Consulta de prueba Markdown/LaTeX:
  - Mensaje: “¿Cómo planteo la integral de superficie para una semiesfera? Usa una fórmula.”
  - Salida: **813 caracteres**, **28 símbolos `$`**, encabezados `##`.
  - El modelo emitió expresiones como `$\mathbf{r}(u,v)$` y `$\mathbf{r}_u \times \mathbf{r}_v$`.
- Pruebas de Fase 2 (modos, reindexación, `$$...$$` y fuera de foco): ver **sección 14.5**.

### 8.4 Frontend

```bash
cd frontend
npx tsc --noEmit
npm run build
```

Resultados:

- `tsc --noEmit`: sin errores.
- `vite build`: correcto.
- Bundle principal: ~628.67 kB (gzip ~191 kB); CSS ~58.04 kB.
- Advertencia de tamaño de chunk (>500 kB) por KaTeX/react-markdown; no bloquea.
- Contenedor frontend con dependencias instaladas:
  - `react-markdown@10.1.0`
  - `remark-math@6.0.0`
  - `rehype-katex@7.0.1`
  - `katex@0.19.1`
- `http://localhost:5173` responde **HTTP 200**.

### 8.5 Modelos disponibles en Ollama

```text
nomic-embed-text:latest
qwen2.5:3b
nomic-embed-text-v2-moe:latest
gemma4:e2b
```

El modelo por defecto del tutor sigue siendo `qwen2.5:3b`.

---

## 9. Ejecución y verificación rápida

### Levantar el sistema

```bash
cd /Luzai_USM
docker compose up -d --build
```

Si el shell no tiene el grupo Docker:

```bash
sg docker -c "docker compose up -d --build"
```

### Verificar servicios

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ramos/MAT024/estado_rag
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173
```

Esperado:

- `health`: `status: ok`.
- `estado_rag`: `fragmentos_indexados` > 0.
- Frontend: `200`.

### Probar el chat por SSE

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"codigo_ramo":"MAT024","mensaje":"¿Qué es una integral de superficie?"}'
```

### Reindexar un ramo

```bash
curl -X POST http://localhost:8000/api/ramos/MAT024/reindexar
```

### Reconstruir frontend tras cambiar dependencias

```bash
sg docker -c "docker compose up -d --build --force-recreate -V frontend"
```

El flag `-V` renueva el volumen anónimo de `node_modules`.

---

## 10. Limitaciones y pendientes

1. **Adherencia del modelo 3B al formato**
   - `qwen2.5:3b` puede ignorar instrucciones de formato.
   - Se reforzó el prompt con una sección obligatoria, un ejemplo concreto y `num_ctx=8192`.
   - Aun así puede producir typos (“Estoya”) o errores factuales; un modelo más grande suele cumplir mejor.

2. **Fórmulas dentro del PDF**
   - Los PDFs son diapositivas; muchas fórmulas están como imagen.
   - No se extraen como LaTeX desde el PDF (0 marcadores `$` en el origen).
   - El LaTeX aparece en las respuestas generadas por el LLM, no necesariamente en el contexto recuperado.

3. **PDFs escaneados**
   - Requieren OCR. Actualmente `pymupdf4llm` advierte que `RapidOCR` no está instalado.
   - Pendiente opcional: agregar `rapidocr-onnxruntime`.

4. **Citas/fuentes en la UI**
   - El backend incluye `[Fuente N: archivo | pág. X]` en el contexto.
   - Pendiente: mostrar esas fuentes como tarjetas o enlaces en el frontend.

5. **Analítica docente**
   - Implementada con `backend/analytics_store.py`, `GET /api/ramos/{codigo}/analytics/resumen` y `frontend/src/views/profesor/AnaliticaDocentePanel.tsx`.
   - Sanitiza correos, RUT, URLs, IPs, IPv6 y teléfonos antes de persistir; agrupa dudas por tópico en Jeff y por similitud léxica en Tutor/Fallback.

6. **Rendimiento del renderizado**
   - ReactMarkdown reparsea el mensaje en cada token durante el streaming.
   - Aceptable para la demo; si se requiere, aplicar throttling/debounce o renderizar texto plano mientras llega el stream.

7. **Tamaño del bundle**
   - KaTeX y react-markdown elevan el bundle a ~628 kB.
   - Opcional: code splitting con `React.lazy` o `manualChunks`.

8. **Jeff semántico**
   - El nivel 1 de Jeff sigue siendo determinista por keywords ($0 GPU).
   - Tareas y FAQs se indexan en ChromaDB y se recuperan en `buscar_fragmentos_planificacion()`; los parafraseos sin keyword se resuelven con RAG + Tutor Socrático.

9. **Badge “Indexado en RAG” hardcodeado**
   - Resuelto: `DocenteView.tsx` usa `archivo.indexado_rag` y `GET /api/ramos/{codigo}/estado_rag`.
   - Resuelto: botón “Reindexar RAG” disponible en **Archivos del curso**.

10. **DOCX no indexados**
    - TEL20425 tiene 4 archivos DOCX además de los PDFs; el pipeline actual solo indexa PDFs.

11. **Configuración de TEL20425 desactualizada**
    - Resuelto: se limpiaron las referencias obsoletas del arreglo `documentos` en `MAT024` y `TEL20425`.

12. **Carpetas de imágenes antiguas**
    - Resuelto: se eliminaron los directorios vacíos con espacios; el respaldo de pruebas quedó en `tests/datos_prueba_respaldo/`.

13. **Guard de alcance heurístico**
    - Se basa en palabras del temario + score de recuperación (`RAG_OFFTOPIC_SCORE=0.65`).
    - Puede fallar con temas del curso que no aparezcan en el temario; BGP y “switch” pasaron correctamente en las pruebas.
    - También puede dejar pasar consultas técnicamente cercanas pero ajenas (por ejemplo, “¿Qué es una red neuronal?”) si el score supera el umbral.

14. **Resumen conceptual sin cierre**
    - El modelo 3B no siempre termina el resumen con las 1-2 preguntas solicitadas; el contenido sí cubre el temario.

---

## 11. Archivos modificados/creados

### Backend

- `backend/rag_engine.py` — motor RAG, reindexación, rutas de imágenes sanitizadas, `RAG_MIN_SCORE`, limpieza de contexto.
- `backend/router_jeff.py` — enrutador administrativo.
- `backend/router_modo.py` — clasificador conceptual/procedimental/general, saludos y alcance del ramo.
- `backend/app.py` — endpoints, auto-reindexación al arranque, chat SSE, modos pedagógicos, guard fuera de foco, `num_ctx`.
- `backend/test_rag.py` — prueba del pipeline RAG.
- `backend/test_jeff.py` — prueba del enrutador Jeff.
- `backend/test_modo.py` — 12 casos del clasificador de modos.
- `backend/data/ramos/MAT024/config.json` — tareas y FAQs.
- `backend/data/ramos/TEL20425/config.json` — tareas, FAQs y reglas socráticas ajustadas para resúmenes conceptuales.
- `backend/.dockerignore` — exclusiones de build.
- `backend/requirements.txt` — dependencias RAG (sin cambios si ya existían).

### Frontend

- `frontend/package.json` — dependencias Markdown/KaTeX.
- `frontend/package-lock.json` — lockfile actualizado.
- `frontend/src/main.tsx` — import de CSS de KaTeX.
- `frontend/src/services/api.ts` — `API_URL` exportado y `resolverUrlApi`.
- `frontend/src/views/alumno/ChatWindow.tsx` — render Markdown/LaTeX.
- `frontend/src/index.css` — estilos `.markdown-content`.
- `frontend/.dockerignore` — exclusiones de build.

### Infraestructura

- `docker-compose.yml` — `:z`, UID/GID, `HOME=/tmp`, telemetría off, `OLLAMA_HOST`/`OLLAMA_LLM_MODEL`, `OLLAMA_NUM_CTX`, `RAG_AUTO_REINDEX`, `RAG_MIN_SCORE`, `RAG_OFFTOPIC_SCORE`.
- Configuración de Ollama en el host — escucha en `0.0.0.0:11434`.
- Grupo Docker del usuario — `knsyx` agregado a `docker` (GID 967).

---

## 12. Referencias internas

- `RAG_documentation.md` — guía técnica del motor RAG.
- `README.md` — arquitectura de contenedores y ejecución.
- `resumen_del_proyecto_ia_usm.md` — estrategia institucional, contrato de datos y planificación.
- `backend/data/ramos/<RAMO>/config.json` — FAQs, tareas y reglas socráticas.

---

## 13. Bitácora corta de comandos

```bash
# Servicios
docker compose up -d --build
sg docker -c "docker compose ps"

# Salud y estado RAG
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ramos/MAT024/estado_rag

# Pruebas backend
docker compose exec backend python test_rag.py --solo-buscar --query "teorema de Stokes"
docker compose exec backend python test_jeff.py

# Frontend local
cd frontend
npm install
npx tsc --noEmit
npm run build

# Rebuild frontend con dependencias nuevas
sg docker -c "docker compose up -d --build --force-recreate -V frontend"
```

---

## 14. Fase 2: reindexación automática y modos pedagógicos

**Fecha:** 2026-11-15  
**Ramos impactados:** TEL20425 y MAT024 (cambios transversales).  
**Estado:** implementado y probado. La reindexación automática queda como solución temporal.

### 14.1 Qué se implementó

1. **Reindexación automática temporal** de ramos con documentos sin indexar al arrancar el backend.
2. **Fase 2: modos pedagógicos** (`conceptual`, `procedimental`, `general`) con prompt específico por modo.
3. **Resúmenes conceptuales**: TEL20425 ahora puede resumir el temario sin entregar comandos ni soluciones completas.
4. **Modo procedimental**: el tutor guía con pistas y preguntas; no entrega configuraciones completas.
5. **Guard de alcance**: consultas ajenas al ramo se redirigen sin responder la trivia.
6. **Guard de cálculo directo**: peticiones como “calcula”, “resuelve” o “cuánto es” con datos reciben una pista inicial, no el resultado final.
7. **Correcciones necesarias para que Fase 2 funcionara** (Fase 3 mínima):
   - `num_ctx=8192` para evitar truncamiento de reglas.
   - Limpieza de artefactos del contexto (imágenes, HTML, énfasis, `\ufffd`).
   - Rutas de imágenes sanitizadas (`_slug_imagenes`) para que `pymupdf4llm` no falle con espacios/acentos.
   - Temperatura `0.2`.

No se implementó una Fase 3 separada: solo los ajustes mínimos necesarios para que los modos pedagógicos y el formato funcionaran.

### 14.2 Plan usado

1. **Diagnosticar TEL20425**: confirmar 0 fragmentos, `indexado_rag=false`, `chroma/` vacío, 8 PDFs con texto y badge de UI hardcodeado.
2. **Habilitar reindexación automática** al arranque para ramos con documentos sin indexar (temporal, controlada por `RAG_AUTO_REINDEX`).
3. **Crear clasificador de modo** (`router_modo.py`) con heurística determinista y pruebas (`test_modo.py`).
4. **Refactorizar el prompt** (`_construir_system_prompt`) para incluir temario, modo, reglas de resumen, prohibición de soluciones completas y formato Markdown/LaTeX.
5. **Corregir rutas de imágenes** y agregar limpieza de contexto.
6. **Ajustar `num_ctx` y temperatura**, y probar con TEL20425/MAT024.
7. **Añadir guard de alcance** determinista para consultas fuera de foco.
8. **Añadir guard de cálculo directo** para no resolver ejercicios completos.
9. **Documentar** cambios, pruebas y limitaciones.

### 14.3 Cambios por archivo

- `backend/router_modo.py` (nuevo)
  - `detectar_modo()`: prioridad procedimental; patrones en primera persona (`configuro`, `calculo`, etc.).
  - `es_solicitud_resumen()`: detecta “resume”, “resumen”, “protocolos”, “temas”.
  - `es_saludo()`: evita tratar saludos/agradecimientos como fuera de foco.
  - `menciona_tema_del_ramo()`: compara la consulta con tokens del temario, palabras meta y términos técnicos.
  - `es_calculo_directo()`: detecta “calcula/resuelve/cuánto es” con datos o temas técnicos; excluye “¿cómo se calcula…?”.

- `backend/test_modo.py` (nuevo)
  - 31 casos (modo, cálculo directo, saludo y alcance); **todos pasan**.

- `backend/rag_engine.py`
  - `MIN_SCORE = RAG_MIN_SCORE` (default `0.25`) y filtrado en `buscar_fragmentos_relevantes()`.
  - `_slug_imagenes()` para sanitizar nombres de PDF y alinear las rutas de imágenes con `pymupdf4llm`.
  - `_limpiar_fragmento()`: quita Markdown de imágenes, comentarios/etiquetas HTML, énfasis `_..._`, `\ufffd` y colapsa saltos.
  - `buscar_contexto_relevante()` ahora reutiliza `buscar_fragmentos_relevantes()`.

- `backend/app.py`
  - `AUTO_REINDEX`, `RAG_OFFTOPIC_SCORE`, `OLLAMA_NUM_CTX`.
  - `_obtener_temario()`: temas a partir de los nombres de PDFs.
  - `_construir_system_prompt(..., modo, es_resumen)`: bloques conceptual/procedimental/general, temario, resumen, fuera de foco y formato.
  - `_reindexar_ramos_pendientes()` + `@app.on_event("startup")` con hilo daemon.
  - `_respuesta_fija()`: emite respuestas deterministas por SSE sin llamar al LLM.
  - `_pista_calculo()`: primera pista socrática según el tipo de cálculo.
  - Chat: detecta modo/resumen, recupera fragmentos, calcula `max_score`, aplica guard de cálculo directo, guard de alcance y emite `modo`/`fuera_de_foco`/`pista_forzada` en SSE.
  - Ollama: `temperature=0.2`, `num_ctx=8192`.

- `backend/data/ramos/TEL20425/config.json`
  - Regla socrática ajustada: permite explicaciones/resúmenes conceptuales breves; prohíbe comandos, configuraciones completas y cálculos resueltos en ejercicios.

- `docker-compose.yml`
  - `OLLAMA_NUM_CTX=${OLLAMA_NUM_CTX:-8192}`
  - `RAG_AUTO_REINDEX=${RAG_AUTO_REINDEX:-1}`
  - `RAG_MIN_SCORE=${RAG_MIN_SCORE:-0.25}`
  - `RAG_OFFTOPIC_SCORE=${RAG_OFFTOPIC_SCORE:-0.65}`

### 14.4 Comportamiento por modo

- **Conceptual**
  - Responde definiciones, comparaciones y resúmenes.
  - Si es resumen, recorre el temario completo en viñetas.
  - Puede dar una explicación breve, pero cierra con preguntas.
  - No entrega soluciones completas de ejercicios.

- **Procedimental**
  - No copia soluciones del contexto.
  - No entrega comandos, configuraciones ni bloques completos.
  - Da pistas generales y preguntas guía.
  - Puede mencionar “qué comando” sin escribir el comando.
  - Si detecta un cálculo directo con datos, devuelve una pista inicial (`pista_forzada: true`) y no llama al LLM.

- **General**
  - Saludos y consultas administrativas.
  - Si no hay relación con el ramo, se redirige con el guard de alcance.

### 14.5 Pruebas y resultados

**Reindexación**

```bash
curl http://localhost:8000/api/ramos/TEL20425/estado_rag
```

- Antes: **0 fragmentos**, `indexado_rag=false`.
- Después: **326 fragmentos** y **301 imágenes**.
- La indexación se dispara automáticamente al arrancar si hay documentos sin indexar.
- Se corrigió el error de rutas con espacios/acentos:
  `cannot open file '.../imagenes/TEL20425_N02_-_Cableado_Estructurado/...png'`.

**Clasificador**

```bash
docker compose exec backend python test_modo.py
```

- **31/31 casos** correctos (modo, cálculo directo, saludo y alcance).

**Recuperación**

| Consulta | Modo | Score top |
|---|---|---:|
| “¿Qué es una VLAN?” | conceptual | 0.715 |
| “Resume los protocolos vistos en el ramo” | conceptual | 0.679 |
| “¿Cómo configuro una VLAN en un switch?” | procedimental | 0.802 |
| “¿Cuál es la capital de Francia?” | general | 0.616 |

**Chat**

- **TEL20425 — resumen**: cubre Cableado Estructurado, Virtualización, STP, VLAN, Direccionamiento IP y Ruteo, Ruteo Dinámico, ACL y Firewall. BGP aparece como ejemplo dentro de Ruteo Dinámico.
- **TEL20425 — configuración de VLAN**: no entrega comandos; da pistas y preguntas guía.
- **MAT024 — integral de superficie**: usa `$...$` y `$$...$$` correctamente tras `num_ctx=8192`, limpieza de contexto y ejemplo de formato.
- **TEL20425 — fuera de foco**: “¿Cuál es la capital de Francia?” devuelve `fuera_de_foco: true` y redirige sin responder “París”.
- **TEL20425 — saludo**: “Hola” se responde normalmente.
- **TEL20425 — temas del curso no listados en el temario**: “¿Qué es BGP?” y “¿Qué es un switch?” pasan el guard por score alto y se responden como contenido del ramo.
- **TEL20425 — cálculo directo**: “Calcula la máscara de subred para 192.168.1.0/24” devuelve `pista_forzada: true` y pregunta por los bits de host; no entrega `255.255.255.0`.
- **TEL20425 — cálculo genérico**: “Calcula 2+2” devuelve una pista genérica, sin el resultado.
- **TEL20425 — ejercicio sin datos**: “Resuelve paso a paso el ejercicio 3” no dispara el guard; el tutor pide el enunciado.
- **TEL20425 — cómo calcular**: “¿Cómo se calcula una máscara de subred?” no dispara el guard; el LLM puede explicar el método (no es un ejercicio concreto).

### 14.6 Variables nuevas

| Variable | Default | Efecto |
|---|---|---|
| `RAG_AUTO_REINDEX` | `1` | Reindexa al arrancar ramos con documentos sin indexar. |
| `RAG_MIN_SCORE` | `0.25` | Umbral mínimo de similitud para usar un fragmento. |
| `RAG_OFFTOPIC_SCORE` | `0.65` | Score mínimo para considerar una consulta dentro del ramo cuando no hay palabra clave. |
| `OLLAMA_NUM_CTX` | `8192` | Ventana de contexto; evita truncar reglas y formato. |

### 14.7 Limitaciones observadas

- El modelo `qwen2.5:3b` aún produce typos (“Estoya”) y errores factuales ocasionales (por ejemplo, atribuir CSMA/CD a switches).
- El resumen conceptual no siempre termina con las 1-2 preguntas solicitadas, aunque el contenido sea correcto.
- El guard de alcance es heurístico: depende de las palabras del temario y del score; puede fallar con subtemas no listados.
- El guard de cálculo directo solo actúa con acciones explícitas (`calcula`, `resuelve`, etc.) y datos/temas; preguntas tipo “¿Cómo se calcula…?” pueden recibir una explicación procedimental del LLM.
- Los DOCX de TEL20425 no se indexan.
- Las respuestas Jeff por keyword siguen siendo deterministas; los parafraseos se resuelven con RAG + Tutor Socrático, no como respuesta fija de Jeff.
- La reindexación manual ya existe en la UI; la automática al arranque se conserva como respaldo.
- Los datos de prueba están aislados en `tests/`; `backend/data/ramos/` y `backend/data/analytics/` quedan sin archivos de prueba.

### 14.8 Próximos pasos sugeridos

1. (Hecho) Botón “Reindexar RAG” y badge real basado en `estado_rag` / `archivo.indexado_rag`.
2. Indexar DOCX (o convertirlos a PDF/Markdown antes de indexar).
3. (Hecho) Limpieza de carpetas vacías y del arreglo `documentos` de TEL20425.
4. Evaluar un modelo 7B para mejorar adherencia factual y de formato.
5. (Hecho) Pruebas automatizadas del guard de alcance, del guard de cálculo directo, del resumen conceptual, RAG de tareas y analítica.
6. (Hecho) Reindexación manual disponible; se conserva la automática al arranque como respaldo.
7. Si se busca un modo socrático estricto, extender el guard de cálculo a preguntas del tipo “¿Cómo se calcula…?”.

---

## 15. Cierre del change `add-docente-analytics-and-jeff-tasks`

- Progreso OpenSpec: `12/12` tareas completadas en `openspec/changes/add-docente-analytics-and-jeff-tasks/tasks.md`.
- RAG de tareas: `backend/rag_engine.py` indexa tareasJeff, las incluye en `buscar_fragmentos_planificacion()` y propaga fallos de eliminación vectorial; los endpoints `POST/PUT/DELETE /api/ramos/{codigo}/tareas` reportan `rag_sincronizado` real.
- CRUD/fallback: carpeta `Planificacion` por defecto; `GET/PUT /api/ramos/{codigo}/config_fallback` con guardado atómico, actualización parcial no destructiva y `canal_alternativo` anexado a las respuestas `FALLBACK_DOCENTE`.
- Vista docente: badge RAG real, conteo de `estado_rag`, botón “Reindexar RAG” y editor de `config_fallback`.
- Analítica: sanitización de identificadores, agrupación léxica de paráfrasis, filtros `canal`/`limite`/`dias`, comparativa por canal y botón “Guardar en Jeff”.
- Aislamiento: suites en `tests/` con `tempfile.TemporaryDirectory()`; sin archivos en `backend/data/ramos/TEST101`, `backend/data/ramos/MAT999` ni `backend/data/analytics/`.

### Verificación ejecutada

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v   # 29 tests, OK
npx tsc --noEmit && npm run build                        # OK (frontend/dist generado)
docker compose config                                    # OK (luzai_usm)
openspec instructions apply --change "add-docente-analytics-and-jeff-tasks" --json  # 12/12
openspec validate add-docente-analytics-and-jeff-tasks --strict --json             # válido, 0 issues
```

### Nota de entorno

- `backend/requirements.txt` mantenido sin cambios. En Python `3.14.10`, el pin `pydantic-core==2.23.4` falla al compilar; la verificación local usó `pydantic 2.14.4`, `fastapi 0.165.0` y dependencias compatibles instaladas en el entorno.
