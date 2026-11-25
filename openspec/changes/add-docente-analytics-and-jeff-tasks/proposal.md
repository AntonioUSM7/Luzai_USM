# Proposal

## Why

La rama `analitic_docente_develop` incorpora borradores sin consolidar de gestión de tareas de Jeff y analítica docente, pero presenta brechas para cerrar el producto final: las tareas de Jeff no cuentan con respaldo semántico en RAG cuando el alumno parafrasea, la vista docente aún tiene el badge `"Indexado RAG"` hardcodeado y no expone edición de `config_fallback`, el subsistema de analítica anónima agrupa preguntas del tutor solo por texto exacto (impidiendo ver las preguntas más frecuentes reales) y carece de comparativa visual Jeff vs. Tutor, y existen archivos de prueba (`backend/test_*.py`) y residuos de datos de prueba (`MAT999/`, `TEST101/`, `Test_Upload/`, carpetas vacías y documentos ajenos) mezclados dentro de `backend/`.

## What Changes

- **Cierre de JEFF y gestión docente**:
  - Formalizar e integrar el CRUD completo de `tareas` de Jeff (API `/api/ramos/{codigo}/tareas`, `router_jeff.py` y `TareasJeffPanel.tsx`) junto con su sincronización vectorial en RAG para responder consultas parafraseadas sin caer en falsos fallbacks.
  - Incluir `"Planificacion"` en las carpetas creadas por defecto en cada ramo, exponer el estado real `indexado_rag` por documento junto a un botón manual de reindexación en `DocenteView.tsx`, y permitir configurar `config_fallback` desde la vista docente.
- **Analíticas anónimas con preguntas más frecuentes reales**:
  - Mejorar `analytics_store.py` para agrupar consultas equivalentes del Tutor Socrático y Fallback mediante normalización léxica sin stopwords y agrupación por similitud/tópico (en lugar de coincidencia exacta de cadena), manteniendo la sanitización *Privacy by Design* y agregando limpieza de teléfonos.
  - Ampliar el resumen agregado (`GET /api/ramos/{codigo}/analytics/resumen`) con filtro/detalle de preguntas frecuentes por canal y visualización comparativa de ahorro Jeff vs. Tutor en `AnaliticaDocentePanel.tsx`, además de una acción rápida para convertir dudas frecuentes en FAQs de Jeff.
- **Separación y limpieza de archivos de prueba**:
  - Mover todos los scripts de prueba (`backend/test_*.py`) y artefactos/fixtures de prueba fuera de `backend/` hacia una carpeta dedicada en la raíz (`tests/`), manteniendo `backend/` y `frontend/` limpios para el producto final y excluyendo `tests/` del build/despliegue.
  - Trasladar/limpiar los residuos de datos de prueba en `backend/data/ramos/` (`MAT999/`, `TEST101/`, `MAT024/imagenes/Test_Upload/`, 8 carpetas vacías con espacios en `TEL20425/imagenes/`, archivo `TEL241-OT4-Lab-GrupoX.docx` y semillas obsoletas de `documentos` en `config.json`), y parchear las pruebas para que usen directorios temporales aislados sin contaminar `backend/data/`.

## Capabilities

### New Capabilities
- `docente-anonymous-analytics`: Registro anónimo en JSONL y panel docente con preguntas más frecuentes agrupadas por similitud léxica y tópico, comparativa visual Jeff vs. Tutor y conversión rápida de dudas frecuentes a FAQs.
- `test-isolation-and-release-hygiene`: Separación física de scripts, fixtures y residuos de prueba fuera de los directorios productivos (`backend/` y `frontend/`), con ejecución aislada en directorios temporales y exclusión en el empaquetado final.

### Modified Capabilities
- `semantic-router`: Gestión CRUD de tareas de Jeff, sincronización semántica de tareas en RAG, creación por defecto de la carpeta `Planificacion` y configuración docente de parámetros de `config_fallback`.
- `course-platform`: Estado real de indexación RAG por documento, acción manual de reindexación en la vista docente y saneamiento de metadatos de documentos en `config.json`.

## Impact

- **Backend**: `backend/app.py`, `backend/router_jeff.py`, `backend/rag_engine.py`, `backend/analytics_store.py`, `backend/.dockerignore`, `.gitignore`.
- **Frontend**: `frontend/src/types.ts`, `frontend/src/services/api.ts`, `frontend/src/views/profesor/DocenteView.tsx`, `frontend/src/views/profesor/TareasJeffPanel.tsx`, `frontend/src/views/profesor/AnaliticaDocentePanel.tsx`.
- **Datos y pruebas**: Reubicación de `backend/test_*.py` hacia `tests/`, limpieza/traslado de residuos en `backend/data/ramos/` (`MAT999/`, `TEST101/`, `MAT024/`, `TEL20425/`) y actualización de `MAT024/config.json` y `TEL20425/config.json`.
