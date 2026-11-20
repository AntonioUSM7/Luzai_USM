# Tasks

## 1. Configuración y Módulo de Prompt Socrático

- [ ] 1.1 Agregar variable de entorno `OLLAMA_MODEL=qwen3:8b` en [docker-compose.yml](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/docker-compose.yml) y leerla en [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) con valor por defecto `qwen3:8b`; verificar que `docker compose config` valida sin errores.
- [ ] 1.2 Crear `backend/socratic_prompt.py` con la función `construir_system_prompt(datos_ramo, contexto_rag="")` que combine las reglas socráticas institucionales (prohibición de soluciones directas/código resuelto y guardrails anti-*prompt injection*), las `reglas_socraticas` del ramo y un bloque opcional para `contexto_rag`; verificar mediante prueba unitaria o script Python que el prompt generado incluye ambos bloques y resiste campos vacíos.

## 2. Backend: Endpoints de Reglas Socráticas y Chat Streaming con Ollama

- [ ] 2.1 Implementar `PUT /api/ramos/{codigo_ramo}/reglas-socraticas` en [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) validando ramo existente (404) y texto no vacío (400), actualizando únicamente `reglas_socraticas` en `config.json`; verificar con `curl` o `TestClient` que persiste el cambio sin alterar `faqs_jeff` ni metadatos.
- [ ] 2.2 Actualizar el modelo `ConsultaChat` y el endpoint `POST /api/chat` en [backend/app.py](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/backend/app.py) para aceptar `historial` opcional de sesión, construir los mensajes (`system`, historial, `user`) y hacer streaming SSE desde `${OLLAMA_HOST}/api/chat` usando `httpx.AsyncClient`; verificar con `TestClient` (mock de Ollama) que emite eventos `token` y `fin`, y que maneja errores de conexión/modelo devolviendo un mensaje legible sin colgar el stream.

## 3. Frontend: Editor Docente de Reglas y Chat Socrático Multi-turno

- [ ] 3.1 Actualizar [frontend/src/types.ts](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/types.ts) y [frontend/src/services/api.ts](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/services/api.ts) para soportar `actualizarReglasSocraticas(codigoRamo, reglas)` y el envío de `historial` acotado en `enviarMensajeChat`; verificar compilación TypeScript (`npm run build` o `tsc --noEmit` en `frontend/`).
- [ ] 3.2 Reemplazar el *placeholder* de la pestaña `subTab === 'socratico'` en [DocenteView.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/profesor/DocenteView.tsx) por un editor funcional de `reglas_socraticas` con botón de guardado, indicador de estado y sincronización del ramo activo en [App.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/App.tsx); verificar visualmente y comprobando que al recargar persiste la regla guardada.
- [ ] 3.3 Actualizar [ChatWindow.tsx](file:///home/antonio/Documents/U/TEL342/Proyecto/Luzai_USM/frontend/src/views/alumno/ChatWindow.tsx) para enviar los últimos mensajes de la sesión como `historial`, mostrar indicador de espera mientras llega el primer token de Ollama y manejar errores de respuesta; verificar compilación TypeScript (`npm run build` en `frontend/`).

## 4. Validación End-to-End con Ollama Local

- [ ] 4.1 Levantar el stack con `docker compose up --build` teniendo Ollama activo en el host (`qwen3:8b` o modelo de prueba), editar las reglas socráticas de `MAT024` desde la vista docente y probar en la vista alumno una consulta matemática y un intento de *prompt injection*, verificando respuestas socráticas en streaming sin soluciones directas.
