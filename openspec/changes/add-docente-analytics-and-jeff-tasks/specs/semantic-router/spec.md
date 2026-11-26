# Spec Delta

## ADDED Requirements

### Requirement: Gestión docente de tareas y entregas administrativas en Jeff
The system SHALL allow teachers to list, create, update, and delete course assignments (`tareas`) with title, due date, submission format, platform, keywords, and optional fixed response, persisting changes atomically per course and intercepting matching student queries in `JEFF_ADMIN` at zero GPU cost.

#### Scenario: Docente crea y actualiza una tarea administrativa de Jeff
- **WHEN** el docente crea o edita una tarea desde la pestaña de Tareas y Entregas con título y palabras clave (o auto-sugeridas desde el título)
- **THEN** el sistema guarda la tarea en la configuración del ramo y Jeff responde de inmediato por `JEFF_ADMIN` ante consultas que coincidan con sus palabras clave

#### Scenario: Docente elimina una tarea existente
- **WHEN** el docente elimina una tarea por su identificador
- **THEN** el sistema la remueve de la configuración del ramo o retorna HTTP 404 si el identificador no existe

### Requirement: Respaldo semántico de tareas en RAG para consultas parafraseadas
The system SHALL index course assignments (`tareas`) into the course vector store alongside `faqs_jeff` upon creation, update, and full reindexing, and remove their vector upon deletion so paraphrased assignment queries are answered with official course data instead of triggering false fallbacks.

#### Scenario: Pregunta parafraseada sobre una tarea sin coincidencia exacta de palabras clave
- **WHEN** un estudiante pregunta sobre una tarea usando términos distintos a sus `palabras_clave` configuradas
- **THEN** Jeff no intercepta por keywords y el canal informativo RAG recupera la tarea indexada como contexto oficial para responder con precisión

### Requirement: Carpeta Planificacion por defecto y configuración docente de fallback
The system SHALL ensure the `Planificacion` folder is included among the default course document directories and SHALL allow teachers to view and update the course's fallback configuration (`habilitado`, `permitir_escalar_profesor`, `mensaje_sin_respaldo`, `mensaje_fuera_de_foco`, `canal_alternativo`) from the teacher interface.

#### Scenario: Carpeta Planificacion disponible al inicializar directorios del ramo
- **WHEN** se consultan las carpetas de documentos de un ramo existente
- **THEN** la carpeta `Planificacion` figura disponible por defecto junto a las carpetas base del curso

#### Scenario: Docente actualiza mensajes y comportamiento de fallback del ramo
- **WHEN** el docente consulta o modifica la configuración de fallback de un ramo desde la vista docente
- **THEN** el sistema valida y persiste los cambios de forma atómica y las respuestas futuras de `FALLBACK_DOCENTE` utilizan los valores actualizados
