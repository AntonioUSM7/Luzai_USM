# LuzAI USM — Tutor Socrático Institucional ("Smartguard" + "Jeff")

Plataforma educativa agéntica para la **Universidad Técnica Federico Santa María (USM)** diseñada bajo metodología de andamiaje cognitivo socrático, con enrutamiento semántico de costo `$0` (**Jeff**) e inferencia local privada (**Ollama + Qwen**).

---

## 1. Arquitectura de Contenedores (Docker)

El proyecto está empaquetado con **Docker Compose** para garantizar compatibilidad total entre los equipos de desarrollo (**Antonio** y **Ahmaru**), manteniendo el motor **Ollama** nativo en el host para aprovechar directamente la GPU (**NVIDIA RTX 5060**).

```
+-------------------------------------------------------------------+
| MÁQUINA HOST                                                      |
|                                                                   |
|  [ Ollama Nativo :11434 ]  <-- GPU NVIDIA RTX 5060 (Qwen 8B)      |
|             ^                                                     |
|             | (host.docker.internal:11434)                        |
|  +----------+--------------------------------------------------+  |
|  | DOCKER COMPOSE                                              |  |
|  |                                                             |  |
|  |  [ Backend FastAPI :8000 ]  <--->  [ Frontend React :5173 ] |  |
|  |   * Smartguard API                  * Interfaz USM          |  |
|  |   * Enrutador "Jeff"                * Streaming SSE         |  |
|  |   * Datos AULA (TEL20425 / MAT024)  * Vista Alumno/Docente  |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
```

---

## 2. Guía Rápida de Ejecución (Paso a Paso)

### Levantar todo el sistema con Docker (Recomendado)

Desde la raíz del proyecto, ejecuta:

```bash
docker compose up --build
```

Una vez iniciado, abre en tu navegador:
* **Interfaz Web (Smartguard React):** http://localhost:5173
* **API Backend (Salud):** http://localhost:8000/api/health
* **Documentación Interactiva (Swagger FastAPI):** http://localhost:8000/docs

Para detener los contenedores:
```bash
docker compose down
```

---

## 3. Explicación de Cada Archivo (Mapa para el Equipo)

### Backend (`/backend`)
* `backend/app.py`: Servidor principal en **FastAPI**. Expone:
  * `GET /api/health`: Verifica que el servidor esté vivo.
  * `GET /api/ramos`: Devuelve los ramos activos (`TEL20425` y `MAT024`) con sus documentos y FAQs.
  * `POST /api/chat`: Recibe la pregunta del alumno, consulta a **Jeff** primero y transmite la respuesta palabra por palabra mediante **Server-Sent Events (Streaming)**.
* `backend/router_jeff.py`: El cerebro de **Jeff**. Normaliza el texto (quita tildes y mayúsculas) y busca coincidencias con las palabras clave administrativas de cada ramo. Si coincide, responde gratis sin usar la GPU.
* `backend/data/ramos/<CODIGO>/config.json`: Simulación de **AULA USM**. Aquí se configuran las fechas de certámenes, salas, libros recomendados y reglas socráticas de cada profesor.
* `backend/data/ramos/<CODIGO>/documentos/`: Carpeta donde **Ahmaru** depositará los PDFs reales del ramo para indexarlos con el motor RAG.

### Frontend (`/frontend`)
* `frontend/src/App.tsx`: Componente raíz que carga la lista de ramos desde FastAPI al iniciar y coordina qué ramo y qué rol (`alumno` o `docente`) están activos.
* `frontend/src/components/Sidebar.tsx`: Barra lateral azul marino USM (`#002B49`) que permite cambiar entre **TEL20425** y **MAT024**, alternar entre modo **Estudiante / Docente**, ver los PDFs cargados y monitorear cuántas llamadas de GPU ha ahorrado **Jeff**.
* `frontend/src/components/ChatWindow.tsx`: Ventana de conversación con soporte de **Streaming en tiempo real** y botones de prueba rápida para demostrar en vivo la diferencia entre una intercepción de Jeff y el Tutor Socrático.
