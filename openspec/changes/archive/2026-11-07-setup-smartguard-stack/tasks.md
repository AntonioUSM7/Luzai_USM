# Tasks

## 1. Backend Base y Simulación de AULA

- [x] 1.1 Crear la estructura de directorios del backend (`backend/`), `backend/requirements.txt` y `backend/Dockerfile` con Python 3.11-slim, verificando la presencia de los archivos.
- [x] 1.2 Configurar el almacenamiento de datos de AULA en `backend/data/ramos/` para `TEL20425` y `MAT024` con sus respectivos archivos `config.json` de prueba (fechas, salas y entregas).
- [x] 1.3 Implementar el servidor FastAPI base (`backend/app.py`) con soporte CORS y endpoints `/api/health` y `/api/ramos`.

## 2. Enrutador Semántico "Jeff" Base

- [x] 2.1 Crear el módulo `backend/router_jeff.py` para cargar los FAQs de cada ramo e interceptar consultas administrativas por coincidencia de palabras clave.
- [x] 2.2 Integrar el enrutador Jeff en `backend/app.py` exponiendo un endpoint `/api/chat` preliminar que devuelva la respuesta estática de Jeff para dudas administrativas o derive a pedagógico.

## 3. Frontend Base (Vite + React + Tailwind USM)

- [x] 3.1 Inicializar el proyecto React con Vite en `frontend/`, crear `frontend/Dockerfile` y configurar Tailwind CSS con los colores institucionales USM (azul marino `#002B49` y amarillo `#F2A900`).
- [x] 3.2 Construir el componente de navegación y selector de asignaturas (`Sidebar.tsx`), permitiendo alternar entre `TEL20425` y `MAT024` y cambiar de rol (Alumno / Docente).
- [x] 3.3 Construir el contenedor principal de chat (`ChatWindow.tsx`) consumiendo la lista de ramos desde `/api/ramos` del backend y mostrando mensajes de prueba.

## 4. Orquestación con Docker Compose e Integración Extremo a Extremo

- [x] 4.1 Crear `docker-compose.yml` en la raíz orquestando `backend` (puerto 8000) y `frontend` (puerto 5173) con volúmenes locales para hot-reload y enlace a Ollama en el host (`host.docker.internal:11434`).
- [x] 4.2 Levantar la pila completa con `docker compose up --build` y verificar mediante el navegador que React consulte exitosamente al backend y que Jeff intercepte preguntas administrativas.
- [x] 4.3 Documentar la guía de ejecución paso a paso en `README.md` con los comandos exactos de Docker para el equipo (Antonio y Ahmaru).
