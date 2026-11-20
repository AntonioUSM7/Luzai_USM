# Tasks

## 1. Configuración y capa de fallback estricto en backend

- [x] 1.1 Agregar el bloque `config_fallback` por defecto en `backend/data/ramos/MAT024/config.json` y `backend/data/ramos/TEL20425/config.json` (habilitado, mensaje estricto, `permitir_escalar_profesor`) y verificar que los JSON cargan sin errores con `python3 -m json.tool`.
- [x] 1.2 Actualizar `POST /api/chat` en `backend/app.py` para emitir la respuesta de canal `FALLBACK_DOCENTE` (`puede_escalar: true`, sin llamar a Ollama) cuando no hay match en Jeff y no hay contexto RAG suficiente o la consulta queda fuera de foco (respetando saludos y resúmenes), verificando con pruebas unitarias en `backend/test_fallback.py` que no se invoca al LLM.

## 2. Buzón de consultas al profesor y conversión a FAQ de Jeff

- [x] 2.1 Implementar almacenamiento thread-safe en `backend/data/ramos/{CODIGO}/consultas_profesor.json` y helper de conversión a `faqs_jeff` en `backend/router_jeff.py` (o módulo auxiliar), verificando con pruebas que leer/escribir consultas y agregar una FAQ mantiene intacto `config.json`.
- [x] 2.2 Exponer en `backend/app.py` los endpoints `POST /api/ramos/{codigo_ramo}/consultas`, `GET /api/ramos/{codigo_ramo}/consultas` y `POST /api/ramos/{codigo_ramo}/consultas/{consulta_id}/responder` (con opción `guardar_en_jeff`, `categoria` y `palabras_clave`), y verificar el ciclo completo (crear -> listar -> responder -> match inmediato en `router_jeff.resolver_consulta`) mediante pruebas en `backend/test_fallback.py`.

## 3. Escalamiento en el chat del estudiante (Frontend)

- [x] 3.1 Extender `enviarMensajeChat` en `frontend/src/services/api.ts` y tipos en `frontend/src/types.ts` para exponer metadatos de eventos SSE (`canal`, `puede_escalar`, `motivo`) y agregar funciones `enviarConsultaProfesor`, `listarConsultasProfesor` y `responderConsultaProfesor`, verificando compilación TypeScript con `npm run build`.
- [x] 3.2 Actualizar `frontend/src/views/alumno/ChatWindow.tsx` para mostrar el botón **"Enviar esta pregunta al profesor"** cuando un mensaje llegue por `FALLBACK_DOCENTE` con `puede_escalar: true`, y cambiar su estado a confirmado tras el `POST`, verificando con `npm run build` y prueba manual en el navegador.

## 4. Buzón docente y verificación integral

- [x] 4.1 Agregar en `frontend/src/views/profesor/DocenteView.tsx` la sección de **Consultas pendientes de alumnos** con acciones para descartar/resolver o responder guardando en `faqs_jeff` (con palabras clave pre-sugeridas editables), verificando compilación con `npm run build`.
- [x] 4.2 Ejecutar la suite de pruebas del backend (`python3 -m pytest` o scripts `test_*.py`) y compilar el frontend (`npm run build`), verificando de extremo a extremo que una pregunta sin respaldo se escala al profesor, se convierte en FAQ de Jeff y en la siguiente consulta responde por `JEFF_ADMIN` a $0 GPU.
