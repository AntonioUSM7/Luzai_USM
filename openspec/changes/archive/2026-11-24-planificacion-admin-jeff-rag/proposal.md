# Proposal

## Why

Cuando un estudiante realiza consultas administrativas o de planificación del curso (por ejemplo, *"¿cuál es la planificación del curso?"*, *"¿qué se ve en la experiencia 3?"* o *"¿cuándo es el certamen final?"*), el flujo anterior bloqueaba las consultas como `fuera_de_foco`, las respondía con tono socrático en vez de datos directos, o las secuestraba con keywords demasiado genéricas en `faqs_jeff` (como `"red"` dentro de un ejercicio de subnetting). Además, no todas las planificaciones docentes vienen en una tabla uniforme, por lo que obligar a parsear/mantener una tabla aparte no escala a todos los ramos.

## What Changes

- **Visor directo de documentos del ramo:** Nuevo endpoint `GET /api/ramos/{codigo_ramo}/documentos/{ruta:path}` (`FileResponse` inline) para que cualquier documento en `documentos/` (incluyendo `Planificacion/` y subcarpetas) se abra directamente en una nueva pestaña del navegador.
- **Desambiguación clicable de documentos de planificación en Jeff ($0 GPU):** Al preguntar de forma general por la planificación del curso, Jeff inspecciona `documentos/Planificacion/` (y sus subcarpetas): si hay 1 archivo devuelve su enlace directo; si hay 2 o más (ej. materia y proyecto), pregunta cuál revisar enviando botones clicables (`sugerencias`) que resuelven al enlace exacto al hacer clic.
- **Canal RAG informativo para consultas puntuales de planificación:** Cuando una consulta tiene intención administrativa/de cronograma (experiencias, clases, fechas, evaluaciones) sin coincidencia exacta en Jeff, `/api/chat` consulta `rag_engine.buscar_fragmentos_planificacion` (cubriendo `Planificacion/`, subcarpetas y `faqs_jeff`), omite el guard `fuera_de_foco`, responde de forma directa (sin reglas socráticas) y adjunta el enlace clicable al documento fuente.
- **Guard anti-secuestro en Jeff:** Mejora en `_coincide` (sin comodín arbitrario `\w*` en palabras ≤ 4 letras) y `_puntuar` para que una palabra genérica aislada no intercepte ejercicios técnicos/procedimentales (ej. `"si quiero una red 10 host, que mascara deberia usar"` pasa al Tutor Socrático).

## Capabilities

### New Capabilities
- `course-schedule-planning`: Acceso directo inline a documentos de planificación, resolución/desambiguación clicable de múltiples documentos en `Planificacion/` a $0 GPU y canal RAG informativo con enlace al documento fuente.

### Modified Capabilities
- `semantic-router`: Incorporar detección de consultas de planificación con desambiguación clicable, protección contra falsos positivos por keywords cortas/genéricas en ejercicios técnicos y enrutamiento al canal RAG informativo antes del guard `fuera_de_foco`.

## Impact

- **Backend:** `backend/app.py` (endpoint `GET /api/ramos/{codigo_ramo}/documentos/{ruta:path}`, canal RAG informativo en `/api/chat`, metadata `sugerencias` en SSE), `backend/router_jeff.py` (`listar_documentos_planificacion`, `_resolver_planificacion_documentos`, guard anti-secuestro en `_coincide`/`_puntuar`), `backend/router_modo.py` (`es_consulta_administrativa_o_planificacion`), `backend/rag_engine.py` (`buscar_fragmentos_planificacion`), `backend/test_jeff.py`.
- **Frontend:** `frontend/src/types.ts`, `frontend/src/services/api.ts`, `frontend/src/views/alumno/ChatWindow.tsx` (botones clicables de desambiguación con envío inmediato para `JEFF_ADMIN`).
