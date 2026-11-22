# Tasks

## 1. Modelo y CRUD de preguntas guardadas en `router_jeff.py` y `consultas_store.py`

- [x] 1.1 Extender `backend/router_jeff.py` para soportar el campo opcional `pregunta` en `agregar_faq_jeff` (con auto-sugerencia de `palabras_clave` desde `pregunta` si vienen vacías) y agregar funciones atómicas `listar_faqs_jeff`, `actualizar_faq_jeff` y `eliminar_faq_jeff`; verificar con pruebas unitarias en `backend/test_jeff.py`.
- [x] 1.2 Actualizar `backend/consultas_store.py` (`responder_consulta`) para pasar `pregunta=objetivo["pregunta"]` al invocar `router_jeff.agregar_faq_jeff`; verificar en `backend/test_fallback.py` que la FAQ creada conserva la pregunta original.

## 2. Sincronización vectorial con ChromaDB en `rag_engine.py`

- [x] 2.1 Agregar `indexar_faq_jeff(codigo_ramo, faq)` y `eliminar_faq_vectorial(codigo_ramo, faq_id)` en `backend/rag_engine.py` usando ID determinista `faq_<id>` y metadata `carpeta="faqs_jeff"`, e incluir las `faqs_jeff` de `config.json` dentro de `_reindexar_ramo`; verificar con pruebas en `backend/test_rag.py` usando embeddings simulados.
- [x] 2.2 Verificar que `buscar_fragmentos_relevantes` y `formatear_contexto` recuperan y formatean las preguntas guardadas como fuente oficial (`Preguntas Guardadas (Jeff)`), y comprobar con prueba unitaria que una consulta parafraseada sin match de keywords en Jeff obtiene contexto RAG positivo.

## 3. Endpoints REST en `backend/app.py`

- [x] 3.1 Implementar en `backend/app.py` los endpoints `GET /api/ramos/{codigo_ramo}/faqs_jeff`, `POST /api/ramos/{codigo_ramo}/faqs_jeff`, `PUT /api/ramos/{codigo_ramo}/faqs_jeff/{faq_id}` y `DELETE /api/ramos/{codigo_ramo}/faqs_jeff/{faq_id}` con sincronización tolerante a fallos hacia `rag_engine`, y conectar la indexación también en `POST /api/ramos/{codigo_ramo}/consultas/{consulta_id}/responder` cuando `guardar_en_jeff=True`.
- [x] 3.2 Agregar pruebas de integración FastAPI (`TestClient`) en `backend/test_jeff.py` (o `backend/test_fallback.py`) cubriendo creación, listado, edición, eliminación (404 si no existe) y flujo `/api/chat` en dos niveles (keyword -> Jeff; parafraseo -> RAG + Tutor); verificar ejecutando `pytest` o `unittest` sobre los tests del backend.

## 4. Apartado de Preguntas Guardadas en la vista docente (Frontend)

- [x] 4.1 Definir el tipo `FaqJeff` en `frontend/src/types.ts` y agregar los métodos `listarFaqsJeff`, `crearFaqJeff`, `actualizarFaqJeff` y `eliminarFaqJeff` en `frontend/src/services/api.ts`; verificar compilación TypeScript (`npm run build` o `npx tsc --noEmit`).
- [x] 4.2 Reemplazar el placeholder de `subTab === 'jeff'` en `frontend/src/views/profesor/DocenteView.tsx` por el panel de Preguntas Guardadas (buscador, formulario crear/editar con pregunta, respuesta, categoría y palabras clave, y botón eliminar con confirmación), y verificar que `npm run build` en `frontend/` finaliza sin errores.
