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

| Dimensión | Simulación a Poca Escala (MVP Local) | Diseño a Gran Escala (Producción Institucional USM) |
| :--- | :--- | :--- |
| **Propósito** | Validar lógica socrática, filtro Smartguard, enrutador "Jeff" e integración RAG a costo $0. | Soportar a miles de estudiantes simultáneos en todos los campus sin cuellos de botella. |
| **Infraestructura de Demostración (Host Principal)** | Servidor *On-Premise* simulado en máquina del Líder (Antonio): **AMD Ryzen 7 5700X, 32 GB RAM, NVIDIA RTX 5060 (8 GB VRAM)**. Capacidad para levantar el modelo LLM más pesado y orquestar todo el stack (Frontend + Backend + IA). | **Nube de Equipos (IaaS / VPC)** arrendando servidores virtuales con GPUs en AWS/Azure. |
| **Infraestructura de Desarrollo de RAG/Jeff** | Estación de trabajo del Técnico (Ahmaru): **AMD Ryzen 7 3700X, 16 GB RAM DDR4, NVIDIA GTX 1660 Ti (6 GB VRAM)**. Ideal para desarrollo modular de Jeff, base vectorial y modelos ágiles de prueba (Qwen de menor escala / embeddings). | Clústeres del mismo modelo Open Source en instancias auto-escalables. |
| **Modelo IA** | Modelo local **Qwen 3.8 8B** (cuantizado Q4_K_M con amplio contexto en la RTX 5060) o modelos ágiles / embeddings (`nomic-embed-text`) vía **Ollama** (`localhost:11434`). | Clústeres de inferencia distribuida de Qwen con vLLM / TGI. |
| **Finanzas** | Inversión $0 (aprovechamiento de hardware propio en ambos equipos). | Modelo **OpEx dinámico**: escalamiento en época de certámenes, apagado en vacaciones. |
| **Seguridad** | Datos confinados al 100% en almacenamiento local. | **Soberanía total de datos**: Sin APIs comerciales externas, garantizando Confidencialidad e Integridad. |

---

## 4. Instrucciones de Trabajo y Colaboración
El desarrollo se coordina aprovechando la potencia de ambos equipos:

### Fase 1: Semanas 1 y 2 (Construcción del MVP)
1.  **Entorno Local e IA Pesada (Antonio en RTX 5060 - 32GB RAM):**
    *   Configurar Ollama con **Qwen 3.8 8B** aprovechando los 8 GB de VRAM y 32 GB de RAM para soportar contextos amplios de RAG sin degradación de velocidad.
    *   Consolidar la interfaz web ("Smartguard" en React + Vite) y los endpoints del Backend (FastAPI).
2.  **Desarrollo del RAG y Enrutador "Jeff" (Ahmaru en GTX 1660 Ti - 16GB RAM):**
    *   Configurar el pipeline de RAG (`backend/rag_engine.py`): ingesta de PDFs, chunking y almacenamiento vectorial (ChromaDB/FAISS) usando embeddings ligeros (`nomic-embed-text`).
    *   Implementar el interceptor semántico "Jeff" (`backend/router_jeff.py`) para resolver consultas administrativas estáticas a costo computacional $0.
    *   Probar sus módulos en local usando modelos ágiles de prueba (ej. Qwen de 3B o versión liviana) en su GTX 1660 Ti.
3.  **Hito de Integración:**
    *   Unir los módulos de Ahmaru (RAG + Jeff) con el Backend y Frontend de Antonio.
    *   Verificar el flujo completo corriendo en la máquina de Antonio con el modelo pesado: Alumno -> Smartguard -> Jeff -> RAG + Qwen 3.8 8B -> Respuesta socrática.

### Fase 2: Semanas 3 y 4 (Afinamiento de IA, Blindaje y Pitch)
1.  **Afinamiento Socrático y RAG Avanzado (Co-desarrollo Antonio & Ahmaru):**
    *   Ajustar el *System Prompt* y la inyección de contexto para garantizar andamiaje cognitivo estricto (cero respuestas resueltas).
    *   Calibrar la precisión de recuperación del RAG por ramos (MAT024, TEL20425, etc.).
2.  **Threat Modeling y Pruebas de Estrés (Antonio & Mathias):**
    *   Ejecutar pruebas de inyección de prompts (Jailbreaks, intentos de saltarse las restricciones socráticas).
    *   Documentar los guardrails bajo la taxonomía OWASP Top 10 for LLMs.
3.  **Cierre Competitivo y Financiero (Mathias con soporte del equipo):**
    *   Medir la métrica de eficiencia: demostrar cuántas consultas resuelve Jeff sin gastar VRAM vs. las que van a la GPU.
    *   Estructurar la comparativa CapEx vs. OpEx institucional y preparar la presentación final.

---

## 5. Estructura de Repositorio (Antigravity)
*   `openspec.yaml` / `README.md`: Especificación de arquitectura y Threat Model (OWASP).
*   `backend/app.py`: Servidor API principal (FastAPI) que orquesta las llamadas.
*   `backend/router_jeff.py`: Lógica de clasificación de intenciones y recursos estáticos.
*   `backend/rag_engine.py`: Ingesta de documentos, base vectorial (Chroma/FAISS) y conexión a Ollama.
*   `frontend/`: Interfaz de usuario (React + Vite) con vistas de alumno y docente.
*   `prompts/socratic_tutor.txt`: Reglas de andamiaje cognitivo.

## 6. Estructura de Integrantes y Planificación

### Planificación Fase 1 (Semanas 1 - 2)

| Rol | Tareas Principales (Semana 2) | Avance / Entregable |
| :--- | :--- | :--- |
| **Líder**<br>Antonio | Desarrollar frontend/backend ("Smartguard"), levantar el modelo IA pesado en local (RTX 5060, 32GB RAM) y co-diseñar la estrategia socrática. | Interfaz web funcional, servidor con modelo LLM pesado operativo y endpoints listos para recibir los módulos RAG y Jeff. |
| **Técnico**<br>Ahmaru | Desarrollar el pipeline RAG y el enrutador administrativo ("Jeff") en su estación de trabajo (GTX 1660 Ti) con modelos ágiles de prueba. | Módulos `rag_engine.py` y `router_jeff.py` probados e integrables con el servidor principal. |
| **Técnico Financiero**<br>Mathias | Iniciar el análisis de infraestructura comparando el uso de Nube de Equipos (IaaS) frente a la compra de hardware físico (CapEx vs. OpEx). | Borrador de matriz de costos y levantamiento inicial de riesgos para el Modelo de Amenazas. |

### Planificación Fase 2 (Semanas 3 - 4)

| Rol | Tareas Principales (Semanas 3 - 4) | Entregable Final |
| :--- | :--- | :--- |
| **Líder**<br>Antonio | Pruebas de estrés y seguridad (Prompt Injection, blindaje), co-desarrollo del comportamiento socrático de la IA, integración final E2E. | Sistema blindado end-to-end, pruebas documentadas de resistencia a manipulación y flujo completo validado. |
| **Técnico**<br>Ahmaru | Refinamiento del RAG (chunking, re-ranking o filtrado por ramo), calibración del prompt socrático con Antonio y optimización de latencia en GPU. | Pipeline RAG preciso y tutor socrático que responde fluidamente guiando con pistas pedagógicas. |
| **Técnico Financiero**<br>Mathias | Consolidar el Modelo de Amenazas (OWASP para LLMs) y armar la presentación comercial destacando el control de costos dinámicos. | Presentación comercial con justificación de escalabilidad financiera (OpEx en nube) y soberanía de datos. |

---

## 7. Especificación Técnica para el Técnico (Módulo Jeff, Recursos y Analítica Docente)

Esta sección define el contrato de datos y la arquitectura técnica que el **Técnico (Ahmaru)** implementará para el enrutador **Jeff**, la ingesta de recursos y el subsistema de analítica anónima para los profesores.

### 7.1. Estructura de Archivos por Asignatura (Almacenamiento Local)
Para garantizar soberanía de datos, latencia mínima y costo $0, cada asignatura se almacena localmente en el servidor backend:

```text
backend/data/ramos/{codigo_ramo}/
├── config.json         # Metadatos del ramo, reglas socráticas, FAQs y tareas de Jeff
└── documentos/         # PDFs de apuntes, guías y rúbricas subidos por el profesor
```

* **Flujo para RAG (`rag_engine.py`):** El módulo RAG debe escanear la carpeta `documentos/` de la asignatura activa, generar los chunks de texto y crear/actualizar los embeddings vectoriales locales (`nomic-embed-text`) usando ChromaDB o FAISS.

---

### 7.2. Contrato de Datos Extendido (`config.json`)
La vista del profesor permitirá guardar y actualizar este archivo. El enrutador `router_jeff.py` debe basarse en esta estructura para resolver consultas administrativas:

```json
{
  "codigo": "MAT024",
  "nombre": "Matemáticas IV",
  "departamento": "Departamento de Matemática",
  "profesor": "Coordinación MAT024 USM",
  "descripcion": "Ecuaciones diferenciales parciales, series de Fourier y cálculo vectorial.",
  "documentos": [
    "Apuntes_Series_de_Fourier_EDP.pdf",
    "Guia_Ejercicios_Certamen_1_MAT024.pdf"
  ],
  "reglas_socraticas": "Guía paso a paso sin resolver integrales ni dar resultados finales.",
  
  "tareas": [
    {
      "id": "tarea_1",
      "titulo": "Tarea 1: Modelación EDP en 2D",
      "fecha_limite": "Viernes 24 de Noviembre, 23:59 hrs",
      "formato_entrega": "Jupyter Notebook (.ipynb) comprimido en .zip junto a informe PDF (máx. 4 páginas)",
      "plataforma": "Buzón de Tareas en AULA USM",
      "palabras_clave": ["tarea 1", "entrega tarea", "formato tarea", "plazo tarea 1", "cuando se entrega la tarea"]
    }
  ],

  "faqs_jeff": [
    {
      "id": "certamen_1",
      "categoria": "Evaluaciones",
      "palabras_clave": ["certamen", "fecha certamen", "cuando es la prueba", "control 1"],
      "respuesta": "📌 [Jeff - Info Administrativa]: El Certamen 1 es el sábado a las 09:00 hrs. Salas se publican 48 hrs antes en AULA."
    },
    {
      "id": "bibliografia",
      "categoria": "Bibliografía",
      "palabras_clave": ["libro", "bibliografia", "texto guia", "zill"],
      "respuesta": "📌 [Jeff - Info Administrativa]: Texto oficial: 'Ecuaciones Diferenciales con Problemas de Frontera' (Dennis Zill)."
    }
  ]
}
```

---

### 7.3. Lógica del Enrutador Semántico (`router_jeff.py`)
El módulo de Jeff debe operar como un interceptor previo a la llamada del LLM:

```text
Entrada: Mensaje del alumno + codigo_ramo
  │
  ├── 1. Normalizar texto (minúsculas, sin tildes)
  │
  ├── 2. ¿Coincide con palabras clave de alguna 'tarea'?
  │      └── SÍ -> Retorna respuesta formateada con fecha, formato y plataforma ($0 cómputo)
  │
  ├── 3. ¿Coincide con palabras clave de alguna 'faq_jeff'?
  │      └── SÍ -> Retorna respuesta directa configurada por el profesor ($0 cómputo)
  │
  └── 4. NO hay coincidencia administrativa
         └── Retorna None -> El backend deriva la consulta al RAG + Qwen 3.8 8B
```

---

### 7.4. Subsistema de Analítica Anónima Docente (*Learning Analytics*)
Para que los profesores conozcan las dudas recurrentes de sus alumnos sin vulnerar la privacidad estudiantil (*Privacy by Design*):

1. **Garantía de Anonimato:**
   * **Nunca** registrar RUT, nombre, correo ni dirección IP.
   * La sesión del estudiante en Smartguard genera un identificador efímero y descartable que no se asocia al log histórico.

2. **Formato del Registro de Evento (`backend/data/analytics/{codigo_ramo}_log.jsonl`):**
   ```json
   {
     "timestamp": "2026-11-08T15:30:00Z",
     "codigo_ramo": "MAT024",
     "canal": "JEFF_ADMIN",
     "topico": "tarea_1_formato",
     "pregunta_anonimizada": "en que formato se manda la tarea 1?"
   }
   ```
   ```json
   {
     "timestamp": "2026-11-08T15:35:12Z",
     "codigo_ramo": "MAT024",
     "canal": "TUTOR_SOCRATICO",
     "topico": "teorema_de_stokes",
     "pregunta_anonimizada": "como parametrizar la frontera de la semiesfera?"
   }
   ```

3. **Métricas que consume el Frontend del Profesor:**
   * **Top 5 Dudas Recurrentes:** Agrupación por palabras clave/tópicos para saber qué materia reforzar en la siguiente clase.
   * **Carga de Consultas por Canal:** Gráfico comparativo de `% Consultas Administrativas (Jeff)` vs. `% Consultas Conceptuales (Tutor)`. Muestra el ahorro de horas docentes y de cómputo GPU.
