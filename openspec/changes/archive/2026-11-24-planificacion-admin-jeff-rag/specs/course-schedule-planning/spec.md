# Spec Delta

## Purpose

Proveer acceso directo a los documentos de planificación del curso, desambiguación clicable en Jeff cuando existen múltiples documentos en `Planificacion/` y respaldo RAG informativo con enlace al documento fuente.

## ADDED Requirements

### Requirement: Visor directo de documentos del ramo desde el chat
The system SHALL serve course documents inline via an HTTP endpoint so students can open planning PDFs and reference files directly from links provided in the chat.

#### Scenario: Apertura de documento de planificación en navegador
- **WHEN** un estudiante hace clic en un enlace `/api/ramos/{codigo_ramo}/documentos/Planificacion/...`
- **THEN** el backend valida que la ruta permanezca dentro del directorio `documentos` del ramo y sirve el archivo con disposición `inline`

### Requirement: Desambiguación clicable de documentos de planificación en Jeff
The system SHALL inspect documents inside `documentos/Planificacion/` (including subfolders) and answer general planning queries at zero GPU cost, returning a direct document link when one file exists or clickable disambiguation options when multiple files exist.

#### Scenario: Un único documento de planificación retorna enlace directo
- **WHEN** un estudiante pregunta *"¿cuál es la planificación del curso?"* y existe un solo archivo en `Planificacion/`
- **THEN** Jeff responde por el canal `JEFF_ADMIN` a $0 GPU con el enlace directo para abrir ese documento

#### Scenario: Múltiples documentos de planificación muestran botones clicables
- **WHEN** un estudiante pregunta *"¿cuál es la planificación del curso?"* y existen dos o más documentos en `Planificacion/` (por ejemplo materia y proyecto)
- **THEN** Jeff responde por `JEFF_ADMIN` preguntando cuál necesita revisar y envía opciones clicables (`sugerencias`) que al presionarse devuelven el enlace directo del documento elegido

### Requirement: Canal RAG informativo para consultas puntuales de planificación
The system SHALL route specific administrative or schedule queries that do not match a static Jeff FAQ to an informative RAG lookup prioritized over `Planificacion/` (including subfolders) and `faqs_jeff`, bypassing `fuera_de_foco` and Socratic withholding rules, and appending the source document link.

#### Scenario: Consulta puntual de cronograma responde en modo informativo con enlace al documento
- **WHEN** un estudiante realiza una consulta puntual de planificación (ej. *"¿qué se ve en la experiencia 3?"* o *"¿qué pasa en septiembre?"*)
- **THEN** el sistema consulta el RAG priorizando `Planificacion/` y `faqs_jeff`, responde de manera directa sin reglas socráticas y adjunta al final el enlace clicable al documento fuente
