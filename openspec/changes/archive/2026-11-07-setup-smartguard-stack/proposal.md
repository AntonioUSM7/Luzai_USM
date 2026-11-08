# Proposal

## Why

El proyecto LuzAI USM requiere una infraestructura base desacoplada, reproducible y confiable que permita al Jefe de Proyecto (Antonio) y al Técnico (Ahmaru) colaborar sin discrepancias de entorno o versiones entre sistemas operativos. Para asegurar la máxima compatibilidad y comprensión de cada pieza, se inicializa el entorno de forma incremental utilizando contenedores Docker (`docker-compose`), articulando un backend en FastAPI (Python), un frontend en React (Vite + Tailwind CSS), y la estructura de datos para los ramos iniciales (TEL20425 y MAT024).

## What Changes

- **Contenedorización con Docker Compose**:
  - `docker-compose.yml` en la raíz para orquestar los servicios con soporte para recarga en vivo (hot-reload mediante volúmenes).
  - `backend/Dockerfile` para empaquetar FastAPI bajo Python 3.11.
  - `frontend/Dockerfile` para empaquetar React + Vite bajo Node 20.
  - Configuración de red para acceder a Ollama en el host (`host.docker.internal:11434`) aprovechando la GPU NVIDIA RTX 5060 local sin sobrecarga de drivers en contenedores.
- **Backend FastAPI Base**:
  - Estructura modular del backend (`backend/app.py`, `backend/requirements.txt`).
  - Endpoints iniciales de salud y consulta de ramos (`/api/health`, `/api/ramos`).
  - Configuración de CORS para permitir la comunicación fluida con el frontend.
- **Estructura de Datos de Ramos (Simulación AULA)**:
  - Creación del directorio de datos `backend/data/ramos/` con soporte para `TEL20425` (Laboratorio de Redes de Computadores) y `MAT024` (Matemáticas IV).
  - Archivos de configuración iniciales (`config.json`) con metadatos y preguntas frecuentes para el enrutador Jeff.
- **Frontend React Base**:
  - Inicialización del proyecto con Vite, React y Tailwind CSS con paleta institucional USM.
  - Vistas base: selector de ramos, panel de cambio de rol (Alumno / Docente) y contenedor de chat con soporte preliminar para streaming de respuestas.

## Capabilities

### New Capabilities
- `course-platform`: Servicio y gestión de ramos simulados de AULA (TEL20425, MAT024), sus recursos documentales y estado de conectividad.
- `semantic-router`: Interceptación y clasificación de intenciones en el servidor web (Jeff) para responder consultas estáticas sin consumo de cómputo GPU.

### Modified Capabilities
*(Ninguna; se trata de la inicialización de capacidades base del proyecto)*

## Impact

- **Código y APIs**: Se crea la raíz del proyecto para `backend/` y `frontend/`, junto a `docker-compose.yml`. Se exponen los endpoints `/api/health` y `/api/ramos`.
- **Dependencias**: Se añaden dependencias Python (`fastapi`, `uvicorn`, `pydantic`), paquetes Node.js (`react`, `react-dom`, `vite`, `tailwindcss`, `lucide-react`) y configuración Docker.
- **Hardware y Entorno**: Garantiza compatibilidad idéntica entre los equipos de desarrollo (Antonio y Ahmaru), manteniendo el acceso nativo a la GPU RTX 5060 del host vía puerto 11434.
