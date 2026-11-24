# Tasks

## 1. Extractor y persistencia de planificación (Backend)

- [x] 1.1 Crear `backend/planificacion_parser.py` para extraer filas tabulares (`clase`, `fecha_201`, `fecha_200`, `tema`, `laboratorio`, `evaluacion`) desde PDFs usando `fitz` (`find_tables`) con fallback a tablas Markdown de `pymupdf4llm`, y verificarlo ejecutando el parser sobre `backend/data/ramos/TEL20425/documentos/Planificacion/Planificacion.pdf` (debe extraer las 18 filas).
- [x] 1.2 Agregar funciones atómicas de lectura, actualización e importación de `planificacion` en `backend/router_jeff.py` (usando `_CONFIG_LOCK`) y verificar que `config.json` conserve intactos `faqs_jeff`, `tareas` y `config_socratica`.
- [x] 1.3 Exponer endpoints `GET /api/ramos/{codigo_ramo}/planificacion`, `PUT /api/ramos/{codigo_ramo}/planificacion` y `POST /api/ramos/{codigo_ramo}/planificacion/importar` en `backend/app.py`, además de disparar la extracción automática al subir un PDF a la carpeta `Planificacion`, verificando con `curl` o `TestClient` que devuelva las filas importadas.

## 2. Enrutamiento administrativo en Jeff y canal RAG informativo

- [x] 2.1 Extender `router_jeff.resolver_consulta` en `backend/router_jeff.py` para resolver consultas sobre `planificacion` (referencias a `experiencia N` / `exp_0N`, `clase N`, evaluaciones como `OT`, `Pres`, `CI`, `CF`, `certamen`, fechas y temas) a $0 GPU por el canal `JEFF_ADMIN`, y agregar pruebas unitarias en `backend/test_jeff.py` que pasen con `pytest`.
- [x] 2.2 Agregar `es_consulta_administrativa_o_planificacion` en `backend/router_modo.py` para detectar intenciones de calendario/programa (sin capturar preguntas puramente conceptuales) y verificarlo con casos de prueba positivos y negativos.
- [x] 2.3 Integrar el canal RAG informativo en `/api/chat` (`backend/app.py`) y búsqueda priorizada por carpeta `Planificacion` en `backend/rag_engine.py`: cuando la consulta sea administrativa sin match exacto en Jeff, consultar `Planificacion` + `faqs_jeff` omitiendo `fuera_de_foco` y usando prompt informativo directo (sin reglas socráticas), verificando con `Planificacion.pdf` indexado que `"que se ve en la experiencia 3?"` responda `STP-RSTP` y `"qué pasa en septiembre?"` responda usando el RAG de `Planificacion`.

## 3. Interfaz docente para gestionar la planificación (Frontend)

- [x] 3.1 Agregar tipos (`FilaPlanificacion`) en `frontend/src/types.ts` y funciones cliente (`obtenerPlanificacion`, `actualizarPlanificacion`, `importarPlanificacionPdf`) en `frontend/src/services/api.ts`, verificando que compilen sin errores TypeScript.
- [x] 3.2 Agregar la sección/sub-pestaña **Planificación** en `frontend/src/views/profesor/DocenteView.tsx` con tabla editable, botón para importar desde un PDF existente de la carpeta `Planificacion` (y reindexar si falta) y guardado, manteniendo la estética minimalista actual y verificando en Vite sin errores de consola.

## 4. Verificación integral

- [x] 4.1 Subir o importar `Planificacion.pdf` en `TEL20425` desde la UI docente, verificar en **Probar Tutor IA** que `"que se ve en la experiencia 3?"`, `"cuando es el certamen final?"` y una pregunta técnica socrática (`"como funciona STP?"`) tomen cada una su canal esperado (`JEFF_ADMIN` vs `TUTOR_SOCRATICO`).
