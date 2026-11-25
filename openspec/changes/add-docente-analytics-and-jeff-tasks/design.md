# Design

## Context

Sobre la rama `analitic_docente_develop` ya existen avances sin commitear para tareas de Jeff (`router_jeff.py`, endpoints `/tareas` en `app.py`, `TareasJeffPanel.tsx`) y analítica anónima (`analytics_store.py`, `/analytics/resumen`, `AnaliticaDocentePanel.tsx`). Sin embargo, la revisión del código y de los `.md` de arquitectura/bitácora reveló bordes abiertos antes de cerrar el producto:
1. En `backend/analytics_store.py`, `_top_dudas` agrupa consultas del Tutor Socrático por cadena normalizada exacta, fragmentando variantes de una misma pregunta frecuente.
2. Las `tareas` de Jeff carecen de respaldo vectorial en `rag_engine.py`, `DocenteView.tsx` aún muestra el badge `"Indexado RAG"` hardcodeado, falta `Planificacion` en `CARPETAS_POR_DEFECTO` y no hay gestión docente de `config_fallback`.
3. Las pruebas (`backend/test_*.py`) viven mezcladas dentro de `backend/` y dos suites (`test_fallback.py`, `test_socratic_config.py`) no parchean `rag_engine.DATA_DIR` ni `analytics_store.ANALYTICS_DIR`, creando directorios `MAT999/` y `TEST101/` en `backend/data/ramos/`. Además persisten residuos de prueba en `backend/data/ramos/` (`Test_Upload/`, carpetas de imágenes vacías con espacios en `TEL20425`, `TEL241-OT4-Lab-GrupoX.docx` y semillas obsoletas en `config.json`).

Ver [proposal.md](./proposal.md) para la motivación completa y el alcance de capacidades.

## Goals / Non-Goals

**Goals:**
- Consolidar todas las capacidades docentes de Jeff (`consultas`, `faqs_jeff`, `tareas`, `Planificacion/`, `config_fallback` y estado RAG real) con respaldo dual determinista ($0 GPU) + semántico (RAG).
- Lograr que el panel de Analítica Anónima muestre **preguntas más frecuentes reales** mediante agrupación determinista ($0 GPU) de variantes equivalentes, junto a comparativa visual Jeff vs. Tutor y acción rápida de conversión a FAQ.
- Aislar completamente código y datos de prueba fuera de `backend/` (en `tests/` y `tests/fixtures/` o `tests/legacy_data/`) para que el producto final (`backend/`, `frontend/` y sus builds Docker) esté libre de archivos y residuos de prueba.

**Non-Goals:**
- No usar llamadas al LLM (Ollama) ni clustering pesado para agrupar analíticas en tiempo de consulta; la agrupación debe ser rápida, determinista y a costo $0 GPU.
- No introducir base de datos relacional ni autenticación/roles reales; se mantiene la persistencia local JSON/JSONL + ChromaDB y el esquema *Privacy by Design* sin sesión de usuario.
- No eliminar documentación histórica de proyecto en raíz (`README.md`, `resumen_del_proyecto_ia_usm.md`, `RAG_documentation.md`, `IMPLEMENTACION_*.md`), aunque podrán actualizarse notas si corresponde al cierre.

## Decisions

### 1. Agrupación determinista de preguntas frecuentes en `analytics_store.py`
- **Decisión**: En `_top_dudas`, cuando el evento trae `topico` (canal `JEFF_ADMIN`), agrupar por `topico` (enriqueciendo la etiqueta con `categoria` o el título/pregunta legible de `config.json` si está disponible). Cuando `topico` es `None` (`TUTOR_SOCRATICO` y `FALLBACK_DOCENTE`), extraer tokens significativos (normalizados, sin tildes, sin signos y filtrando stopwords en español) y agrupar consultas con similitud de Jaccard `>= 0.5` (o coincidencia de tokens técnicos clave) contra grupos ya formados en el mismo canal, conservando la pregunta representativa más frecuente o más corta y un contador de variantes.
- **Alternativa descartada**: Usar embeddings (`nomic-embed-text`) en cada lectura de `GET /analytics/resumen` o al registrar eventos. Se descartó porque acopla la analítica a Ollama encendido, añade latencia y viola el principio de analítica ligera de costo $0.
- **Privacidad**: Reforzar `anonimizar_pregunta` para redactar también números telefónicos chilenos/genéricos (`+56 9 ...`, secuencias de 8-9 dígitos) además de emails, RUTs, URLs e IPs, y soportar parámetro opcional `canal` y `limite` (default 10 o 5 configurable) en `resumen()`.

### 2. Respaldo semántico de `tareas` en `rag_engine.py`
- **Decisión**: Replicar el patrón de `faqs_jeff` (`CARPETA_FAQS_JEFF`) para `tareas` usando id vectorial `tarea_{tarea_id}` y `carpeta = "tareas_jeff"` (o incluir `tareas_jeff` dentro del filtro de `buscar_fragmentos_planificacion` y `buscar_fragmentos_relevantes`). Al crear/actualizar/eliminar en `app.py` (`/api/ramos/{codigo}/tareas`), sincronizar de forma tolerante a fallos (`_sincronizar_tarea_rag` / `_eliminar_tarea_rag`, similar a `_sincronizar_faq_rag`) e incluir `sincronizar_tareas_jeff` dentro de `reindexar_ramo()`.
- **Alternativa descartada**: Dejar `tareas` solo en `router_jeff.py`. Se descartó porque rompe la paridad con `faqs_jeff` cuando los alumnos parafrasean dudas de entregas.

### 3. Completitud de vista docente (`DocenteView.tsx`, `AnaliticaDocentePanel.tsx`)
- **Decisión**:
  - En pestaña **Archivos del curso**: usar `archivo.indexado_rag` real para mostrar badge verde (`Indexado RAG`) o ámbar (`Pendiente`), agregar indicador de fragmentos desde `GET /api/ramos/{codigo}/estado_rag` y botón `"Reindexar RAG"` que invoque `POST /api/ramos/{codigo}/reindexar`.
  - En `app.py`: agregar `"Planificacion"` a `CARPETAS_POR_DEFECTO`.
  - Exponer `GET/PUT /api/ramos/{codigo}/config_fallback` en `app.py` y agregar su sección editable dentro de `DocenteView.tsx` (en la pestaña `socratico` o `consultas` como bloque colapsable de comportamiento ante falta de respaldo).
  - En `AnaliticaDocentePanel.tsx`: agregar barra comparativa visual (`% Jeff` vs `% Tutor Socrático` vs `% Derivación`), selector/filtro por canal en `Top dudas frecuentes`, etiqueta legible de tópico/variantes y botón `"Guardar en Jeff"` que abra el formulario de `Preguntas Guardadas` prellenado.

### 4. Estructura de pruebas y saneamiento del producto final
- **Decisión**:
  - Mover `backend/test_*.py` a una carpeta raíz `/tests/` (por ejemplo `tests/backend/test_*.py` junto a `tests/conftest_paths.py` o helper compartido para agregar `backend/` a `sys.path` y aislar por defecto `BASE_DATA_DIR`, `router_jeff.DATA_DIR`, `consultas_store.DATA_DIR`, `rag_engine.DATA_DIR` y `analytics_store.ANALYTICS_DIR` en `tempfile.TemporaryDirectory`).
  - Crear `tests/datos_prueba_respaldo/` (ignorado por Git o dentro de `tests/fixtures/` según corresponda) para mover ahí los artefactos de prueba/ajenos encontrados en `backend/data/ramos/` antes de purgar `backend/data/ramos/`:
    - `MAT999/` y `TEST101/` (residuos de ChromaDB generados por tests -> eliminar o respaldar fuera de `backend/`).
    - `MAT024/imagenes/Test_Upload/` (PNGs residuales de `Test_Upload.pdf`).
    - 8 carpetas vacías con espacios en `TEL20425/imagenes/TEL20425 N02..N09`.
    - `TEL20425/documentos/Tareas/TEL241-OT4-Lab-GrupoX.docx` (mover a carpeta de respaldo de prueba fuera de `backend/data/ramos/`).
    - `MAT024/imagenes/Clase1..Clase17/` y `MAT024/chroma/` (mover a carpeta de respaldo fuera de `backend/data/ramos/` dado que `MAT024/documentos/` no tiene PDFs actualmente, dejando `MAT024` limpio para ingesta productiva).
    - Limpiar `documentos` en `MAT024/config.json` y `TEL20425/config.json` para que no referencien PDFs inexistentes.
  - Verificar `docker-compose.yml` y `backend/.dockerignore` / `frontend/.dockerignore`: al estar `/tests/` en la raíz fuera de `./backend` y `./frontend`, ni los `COPY . .` de los Dockerfiles ni los bind mounts `./backend:/app` y `./frontend:/app` contendrán scripts ni datos de prueba en el producto final.
- **Alternativa descartada**: Dejar los archivos en `backend/tests/` dentro de `backend/`. Aunque `.dockerignore` los excluiría de la imagen, el `volumes: ./backend:/app:z` de `docker-compose.yml` seguiría montándolos dentro del contenedor en ejecución. Moverlos a la raíz `/tests/` garantiza exclusión total tanto en build como en runtime.

## Risks / Trade-offs

- **Riesgo de agrupación excesiva en `_top_dudas` (falsos positivos con Jaccard bajo)** → Mitigación: usar umbral conservador (`>= 0.5`), exigir al menos 2 tokens significativos en común (o coincidencia exacta si la pregunta tiene 1 solo token significativo) y mantener la agrupación aislada por `canal`.
- **Traslado de `MAT024/chroma` y `MAT024/imagenes/Clase1..Clase17`** → Mitigación: moverlos a la carpeta de respaldo fuera de `backend/` en lugar de borrarlos irreversiblemente, de modo que puedan restaurarse si se necesitan antes de cargar los PDFs finales de MAT024.
- **Importaciones en `tests/` tras mover `backend/test_*.py`** → Mitigación: agregar la ruta de `backend/` a `sys.path` en un módulo común de soporte en `tests/` y ejecutar `python3 -m unittest discover -s tests` (tanto en host como validando sintaxis/imports) como criterio de aceptación.
