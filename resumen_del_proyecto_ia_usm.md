# Estrategia Institucional de IA para el Aprendizaje - Universidad USM
**Documento de Especificación (OpenSpec) y Plan de Acción**

## 1. Visión General del Proyecto
El proyecto nace como respuesta a un incidente crítico en la USM (40% de los informes finales presentaron uso no regulado de IA generativa). El objetivo principal es abandonar el enfoque punitivo y desarrollar un **tutor socrático agéntico** institucional. Este sistema guiará el aprendizaje activo mediante pistas y andamiaje cognitivo, garantizando que **jamás entregue respuestas directas ni código resuelto**.

---

## 2. Arquitectura Técnica y Flujo del Sistema (OpenSpec Core)
El sistema opera bajo un modelo Cliente-Servidor donde la frontera de seguridad se divide en cuatro componentes:

*   **Interfaz Web Privada ("Smartguard"):** Es el frontend donde interactúan alumnos y docentes. Actúa como frontera de seguridad (*system boundary*), aislando cada sesión y filtrando entradas maliciosas (*Prompt Injection*) antes de llegar al modelo.
*   **Enrutador Semántico ("Jeff"):** Un clasificador de intenciones ligero en el servidor web.
    *   *Ruta Administrativa:* Si se solicitan fechas, enlaces o bibliografía (ej. "Libro para MAT024"), Jeff devuelve el dato exacto configurado por el profesor. Gasta $0 en cómputo y evita alucinaciones.
    *   *Ruta Pedagógica:* Si la consulta es de razonamiento, la deriva al motor de IA.
*   **Orquestador de Contexto (System Prompt + RAG):** Ensambla un paquete único por consulta:
    *   *System Prompt:* Reglas invisibles que fuerzan el comportamiento de tutor socrático.
    *   *RAG:* Base vectorial con los PDFs, rúbricas y apuntes del profesor.
    *   *Historial:* Contexto privado de la sesión del alumno.
*   **Motor LLM:** Procesa el contexto y devuelve la pista pedagógica a la interfaz.

---

## 3. Despliegue en Dos Capas: Simulación vs. Gran Escala

| Dimensión | Simulación a Poca Escala (Tu MVP Local) | Diseño a Gran Escala (Producción Institucional USM) |
| :--- | :--- | :--- |
| **Propósito** | Validar lógica socrática, filtro Smartguard, enrutador "Jeff" e integración RAG a costo $0. | Soportar a miles de estudiantes simultáneos en todos los campus sin cuellos de botella. |
| **Infraestructura** | Servidor *On-Premise* simulado en máquina local con GPU **NVIDIA RTX 5060 (8 GB VRAM)**. | **Nube de Equipos (IaaS / VPC)** arrendando servidores virtuales con GPUs en AWS/Azure. |
| **Modelo IA** | Modelo local **Qwen 3 8B** (o Qwen 2.5) cuantizado a 4 bits ejecutado vía **Ollama** (puerto `11434`). | Clústeres del mismo modelo Open Source en instancias auto-escalables. |
| **Finanzas** | Inversión $0 (aprovechamiento de hardware propio). | Modelo **OpEx dinámico**: escalamiento en época de certámenes, apagado en vacaciones. |
| **Seguridad** | Datos confinados al 100% en el disco duro local. | **Soberanía total de datos**: Sin APIs comerciales externas, garantizando Confidencialidad e Integridad. |

---

## 4. Instrucciones para el Jefe de Proyecto (Líder)
Tu rol combina la dirección de arquitectura con el desarrollo directo del servidor web (Smartguard) y el enrutador ("Jeff").

### Fase 1: Semanas 1 y 2 (Construcción del MVP)
1.  **Entorno Local:** Instalar Ollama en tu equipo (RTX 5060) y descargar Qwen 3 8B (o Qwen 2.5 de 7B) en formato cuantizado para que ocupe ~5GB de VRAM.
2.  **Desarrollo de "Smartguard":** Programar la interfaz web (usando Streamlit, Gradio o FastHTML) con manejo de `session_state` para mantener historiales aislados. Conectar esta interfaz a la API local de Ollama (`localhost:11434`).
3.  **Hito de Integración:** Unir tu interfaz web con el módulo **RAG** (a cargo de tu compañero Técnico). Subir un PDF de prueba y verificar que el modelo responda en base a él.

### Fase 2: Semanas 3 y 4 (Enrutador, Blindaje y Pitch)
1.  **Desarrollo de "Jeff":** Programar el interceptor semántico en tu servidor web. Configurar un diccionario base para responder automáticamente consultas administrativas sin llamar a Ollama.
2.  **Threat Modeling (OWASP):** Implementar guardrails en la interfaz para bloquear *Prompt Injections*. Hacer pruebas de estrés al *System Prompt* para asegurar que Qwen jamás resuelva la tarea completa.
3.  **Cierre Competitivo:** Asegurar que el Financiero justifique el ahorro computacional de "Jeff" y la privacidad de la Nube IaaS en el modelo de costos. Reunir capturas de pantalla (uso de VRAM, intercepciones de Jeff) para la presentación.

---

## 5. Estructura de Repositorio (Antigravity)
*   `openspec.yaml` / `README.md`: Especificación de arquitectura y Threat Model (OWASP).
*   `app.py`: Servidor web principal e interfaz de usuario (Smartguard).
*   `router_jeff.py`: Lógica de clasificación de intenciones y recursos estáticos.
*   `rag_engine.py`: Ingesta de PDFs y búsqueda vectorial (Ollama).
*   `prompts/socratic_tutor.txt`: Reglas de andamiaje cognitivo.

## 6. Estructura de Integrantes

### Planificación Fase 1 (Semanas 1 - 2)

| Rol | Tareas Principales (Semana 2) | Avance |
| :--- | :--- | :--- |
| **Líder**<br>Antonio | Desarrollar la interfaz web (el "Smartguard") usando herramientas rápidas (ej. Streamlit o Open WebUI). | Interfaz web capaz de recibir una consulta y enviarla al servidor local, encapsulando la sesión. |
| **Técnico**<br>Ahmaru | Desplegar el modelo base (Qwen 3 8B) e implementar la primera versión del **sistema RAG** para indexar documentos de prueba. | IA local respondiendo preguntas basándose únicamente en un PDF de prueba inyectado por el RAG. |
| **Técnico Financiero**<br>Mathias | Iniciar el análisis de infraestructura comparando el uso de Nube de Equipos (IaaS) frente a la compra de hardware físico (CapEx vs. OpEx). | Elaborar el borrador de la matriz de costos. Realizar el levantamiento inicial de riesgos para estructurar el Modelo de Amenazas. |

### Planificación Fase 2 (Semanas 3 - 4)

| Rol | Tareas Principales (Semanas 3 - 4) | Entregable Final |
| :--- | :--- | :--- |
| **Líder**<br>Antonio | Integrar a "Jeff" (Enrutador Semántico) para desviar consultas administrativas estáticas. Ejecutar pruebas de estrés de prompt injection. Tener lista la prueba a menor escala con IA local. | Sistema final robusto que ahorra recursos al no usar IA pesada para dudas básicas, blindado contra manipulación. Pruebas con IA local enseñando cómo funciona. |
| **Técnico**<br>Ahmaru | Refinar la precisión del **RAG** y ajustar el System Prompt para forzar el andamiaje cognitivo estricto (tutoría socrática). Conectarla con el servidor (Back y Front). | El agente ya no da respuestas directas bajo ninguna circunstancia, guiando al alumno solo con pistas. |
| **Técnico Financiero**<br>Mathias | Consolidar el Modelo de Amenazas (OWASP para LLMs) y armar la presentación comercial destacando el control de costos dinámicos. | Armar la presentación comercial enfocada en destacar el control de costos dinámicos. Justificar estratégicamente la escalabilidad financiera del sistema (para soportar épocas de exámenes) y la soberanía/privacidad de los datos. |
