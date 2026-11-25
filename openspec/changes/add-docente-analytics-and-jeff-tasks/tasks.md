# Tasks

## 1. Aislamiento de pruebas y limpieza del producto final

- [x] 1.1 Crear la estructura raíz `tests/` (con helper de rutas para importar `backend/` y fixture común de aislamiento temporal) y trasladar `backend/test_analytics.py`, `backend/test_fallback.py`, `backend/test_jeff.py`, `backend/test_modo.py`, `backend/test_rag.py` y `backend/test_socratic_config.py` dentro de `tests/`; verificar que `backend/` ya no contiene archivos `test_*.py` y que `python3 -m unittest discover -s tests -p "test_*.py"` descubre todas las suites.
- [x] 1.2 Parchear en `tests/test_fallback.py`, `tests/test_socratic_config.py` y en cualquier nueva prueba las rutas `rag_engine.DATA_DIR`, `rag_engine._clientes` y `analytics_store.ANALYTICS_DIR` hacia `tempfile.TemporaryDirectory()`; verificar ejecutando la suite que no se crean carpetas ni archivos en `backend/data/ramos/` ni `backend/data/analytics/`.
- [x] 1.3 Trasladar los residuos y datos de prueba fuera de `backend/data/ramos/` hacia `tests/datos_prueba_respaldo/` (`MAT999/`, `TEST101/`, `MAT024/imagenes/Test_Upload/`, `MAT024/imagenes/Clase1..Clase17/`, `MAT024/chroma/`, `TEL20425/documentos/Tareas/TEL241-OT4-Lab-GrupoX.docx`) y eliminar las 8 carpetas vacías con espacios en `TEL20425/imagenes/TEL20425 N02..N09`; verificar el árbol de `backend/data/` y actualizar `.gitignore` para excluir `tests/datos_prueba_respaldo/` si contiene binarios pesados.
- [x] 1.4 Limpiar las referencias obsoletas del arreglo `"documentos"` en `backend/data/ramos/MAT024/config.json` y `backend/data/ramos/TEL20425/config.json`, y verificar que `backend/.dockerignore` / `docker-compose.yml` no incluyan `tests/` ni datos de prueba en los contenedores del producto final.

## 2. Cierre de JEFF para docentes y estado RAG real

- [x] 2.1 Extender `backend/rag_engine.py` con `indexar_tarea_jeff`, `eliminar_tarea_vectorial` y `sincronizar_tareas_jeff` (incluyendo las tareas en `reindexar_ramo()` y en `buscar_fragmentos_planificacion()`), y conectar la sincronización tolerante a fallos en los endpoints `POST/PUT/DELETE /api/ramos/{codigo_ramo}/tareas` de `backend/app.py`; verificar con pruebas unitarias en `tests/test_rag.py` y `tests/test_jeff.py` que una consulta parafraseada sobre una tarea sin keyword exacta recupera la tarea vía RAG.
- [x] 2.2 Agregar `"Planificacion"` a `CARPETAS_POR_DEFECTO` en `backend/app.py` e implementar los endpoints `GET /api/ramos/{codigo_ramo}/config_fallback` y `PUT /api/ramos/{codigo_ramo}/config_fallback` con guardado atómico bajo `router_jeff._CONFIG_LOCK`; verificar con pruebas `TestClient` en `tests/test_fallback.py` y `tests/test_jeff.py` cubriendo CRUD HTTP de `/tareas`, carpeta por defecto `Planificacion` y validación/persistencia de `config_fallback`.
- [x] 2.3 Actualizar `frontend/src/types.ts`, `frontend/src/services/api.ts` y `frontend/src/views/profesor/DocenteView.tsx` para: (a) mostrar el badge real `Indexado RAG` vs `Pendiente` según `archivo.indexado_rag`, (b) mostrar el conteo de `estado_rag` y agregar el botón `"Reindexar RAG"` en la pestaña **Archivos del curso**, y (c) añadir la edición de `config_fallback` en la vista docente; verificar con `npx tsc --noEmit` y `npm run build` en `frontend/`.

## 3. Analítica anónima y preguntas más frecuentes

- [x] 3.1 Reforzar `anonimizar_pregunta` en `backend/analytics_store.py` para redactar teléfonos además de emails, RUTs, URLs e IPs, y actualizar `_top_dudas` y `resumen` para agrupar consultas equivalentes en `TUTOR_SOCRATICO` y `FALLBACK_DOCENTE` mediante similitud léxica sin stopwords (conservando agrupación por `topico` con etiqueta legible en `JEFF_ADMIN`), agregando soporte de parámetros opcionales `canal` y `limite` en `GET /api/ramos/{codigo_ramo}/analytics/resumen`; verificar con pruebas unitarias en `tests/test_analytics.py` que variantes parafraseadas se consolidan en una misma duda frecuente.
- [x] 3.2 Agregar pruebas de integración en `tests/test_analytics.py` verificando que `POST /api/chat` (en canales `JEFF_ADMIN`, `TUTOR_SOCRATICO` y `FALLBACK_DOCENTE`) registra eventos sanitizados y `GET /api/ramos/{codigo_ramo}/analytics/resumen` retorna conteos y top dudas correctos sin exponer identificadores ni escribir en `backend/data/analytics/`.
- [x] 3.3 Actualizar `frontend/src/types.ts`, `frontend/src/services/api.ts`, `frontend/src/views/profesor/AnaliticaDocentePanel.tsx` y `frontend/src/views/profesor/DocenteView.tsx` para renderizar una barra/gráfico comparativo de `% Jeff` vs `% Tutor Socrático` vs `% Derivación docente`, selector de canal en `Top dudas frecuentes` con conteo de variantes/tópico, y botón `"Guardar en Jeff"` en dudas de Tutor/Fallback que abra el formulario de Preguntas Guardadas prellenado; verificar compilación con `npx tsc --noEmit` y `npm run build`.

## 4. Verificación integral de cierre

- [x] 4.1 Ejecutar la suite completa de pruebas desde la raíz (`python3 -m unittest discover -s tests -p "test_*.py" -v`) y confirmar que todos los tests pasan y que `backend/data/ramos/` y `backend/data/analytics/` permanecen libres de archivos de prueba.
- [x] 4.2 Ejecutar `npx tsc --noEmit && npm run build` en `frontend/` y `docker compose config` en la raíz para verificar que frontend, backend y configuración de contenedores quedan listos para despliegue sin archivos de prueba.

## Workflow follow-up

- Revisar el diff consolidado en `analitic_docente_develop` antes de hacer commit/PR y archivar los cambios OpenSpec completados (`add-docente-analytics-and-jeff-tasks`, `qwen-socratic-teacher-config`, `strict-fallback-teacher-escalation`) cuando corresponda.
