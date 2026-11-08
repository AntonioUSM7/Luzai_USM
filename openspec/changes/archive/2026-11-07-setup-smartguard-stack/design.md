# Design

## Context

El proyecto se desarrolla en un equipo colaborativo (Antonio como Jefe de Proyecto y Ahmaru como Técnico) sobre plataformas locales con inferencia local prevista (NVIDIA RTX 5060 + Ollama). Ver `proposal.md` para la motivación. Se requiere construir la base técnica que soportará "Smartguard" (interfaz segura) y "Jeff" (enrutador semántico), garantizando reproducibilidad total y evitando desajustes de versiones de librerías mediante Docker.

## Goals / Non-Goals

**Goals:**
- Establecer una separación limpia y desacoplada entre backend (`backend/`) y frontend (`frontend/`), orquestados mediante `docker-compose`.
- Asegurar recarga en vivo (hot-reload) dentro de los contenedores mediante volúmenes enlazados (`bind mounts`).
- Simular la estructura de datos de AULA mediante el sistema de archivos (`data/ramos/`) para TEL20425 y MAT024.
- Configurar endpoints iniciales (`/api/health`, `/api/ramos`) y habilitar CORS para desarrollo local.
- Configurar la interfaz React con Vite y Tailwind CSS estilizada con los colores institucionales USM.
- Permitir al backend en Docker conectarse al servicio Ollama que corre nativamente en el host (`host.docker.internal:11434`).

**Non-Goals:**
- Contenedorizar Ollama con passthrough de GPU complejo: Ollama se mantiene corriendo de forma nativa en el host para evitar problemas de compatibilidad con drivers NVIDIA y el toolkit de contenedores, maximizando los 8 GB de VRAM de la RTX 5060.
- Bases de datos relacionales pesadas (PostgreSQL/MySQL): la simulación de AULA se basará en archivos locales JSON y directorios para facilidad de RAG y demo.
- Autenticación institucional compleja (OAuth2/SSO USM): se utilizará un selector de rol simulado (Alumno / Docente).

## Decisions

### 1. Orquestación con Docker Compose
- **Decisión**: Crear `docker-compose.yml` con dos servicios: `backend` (FastAPI) y `frontend` (Vite/React).
- **Razón**: Permite a cualquier miembro del equipo levantar todo el sistema con un solo comando (`docker compose up --build`), garantizando exactamente las mismas versiones de Python y Node. Se montan volúmenes para que los cambios en el código se reflejen instantáneamente sin reconstruir la imagen.
- **Alternativas consideradas**:
  - *Instalación local directa (venv + npm local)*: Riesgo recurrente de conflictos de versiones entre los entornos de Antonio y Ahmaru.

### 2. Backend: FastAPI (Python 3.11 en Docker)
- **Decisión**: Utilizar FastAPI sobre Flask o Django dentro de una imagen `python:3.11-slim`.
- **Razón**: Manejo nativo de concurrencia asíncrona, soporte directo para respuestas en streaming (SSE) que se usarán en el chat, generación automática de documentación Swagger en `/docs`, e integración nativa con los scripts de RAG.
- **Alternativas consideradas**:
  - *Flask*: Menos soporte nativo para streaming asíncrono moderno y tipado estricto.

### 3. Frontend: React con Vite y Tailwind CSS (Node 20 en Docker)
- **Decisión**: Utilizar Vite + React con Tailwind CSS en un contenedor `node:20-alpine`.
- **Razón**: Permite construir componentes reactivos de alta calidad, rápidos de prototipar y con Hot Module Replacement (HMR) expuesto en el puerto 5173.
- **Alternativas consideradas**:
  - *Streamlit*: Rápido, pero restrictivo para lograr una interfaz universitaria personalizada con roles y paneles docentes.

### 4. Conexión con Ollama en el Host
- **Decisión**: Configurar `extra_hosts: ["host.docker.internal:host-gateway"]` en el servicio del backend en Docker Compose.
- **Razón**: Hace que el contenedor de FastAPI pueda invocar a `http://host.docker.internal:11434` sin importar si el host es Linux o Windows, accediendo directamente a la GPU física.

### 5. Simulación de Recursos de AULA mediante Sistema de Archivos
- **Decisión**: Modelar cada asignatura como una carpeta en `backend/data/ramos/<CODIGO>/` con `config.json` para Jeff y subcarpeta `documentos/` para RAG.
- **Razón**: Permite a Jeff leer preguntas frecuentes directamente sin latencia ni costo computacional, y facilita a Ahmaru indexar los PDFs de cada ramo de forma independiente.

## Risks / Trade-offs

- **[Diferencias de permisos de archivos en Linux con Docker]** → Se configuran usuarios y montajes estándar para evitar conflictos de escritura en carpetas locales.
- **[Resolución de host.docker.internal en Linux]** → Se incluye explícitamente `extra_hosts` con `host-gateway` en `docker-compose.yml` para garantizar que Linux resuelva el host correctamente.
