# semantic-router Specification

## Purpose

Permite clasificar e interceptar intenciones de consulta en el servidor web (Jeff) para responder dudas administrativas de asignaturas sin consumir cómputo en el motor de inferencia LLM.

## Requirements

### Requirement: Interceptación de consultas administrativas
The system SHALL classify queries and respond with preconfigured course FAQ information when matches occur. El sistema debe interceptar consultas administrativas.

#### Scenario: Consulta administrativa reconocida para un ramo
- **WHEN** un estudiante envía una consulta que contiene palabras clave asociadas a fechas o salas de TEL20425
- **THEN** el sistema retorna la respuesta administrativa estática configurada sin invocar el modelo de lenguaje

#### Scenario: Consulta pedagógica no administrativa
- **WHEN** un estudiante envía una consulta de razonamiento técnico o conceptual que no coincide con las preguntas frecuentes
- **THEN** el sistema clasifica la consulta como pedagógica para ser procesada por el orquestador socrático

### Requirement: Persistencia de pregunta original y respaldo dual en FAQs de Jeff
The system SHALL preserve the original `pregunta` text when saving a teacher-resolved query into `faqs_jeff` and maintain deterministic keyword interception at zero GPU cost alongside vector synchronization for the Socratic tutor.

#### Scenario: Escalación resuelta guardada en Jeff conserva la pregunta original
- **WHEN** el docente resuelve una consulta escalada marcando la opción de guardar en Jeff
- **THEN** la entrada creada en `faqs_jeff` incluye la `pregunta` original de la consulta además de `palabras_clave`, `categoria` y `respuesta`, quedando disponible tanto para coincidencia por palabras clave en Jeff como para recuperación semántica en RAG

#### Scenario: Coincidencia exacta por palabras clave mantiene prioridad en Jeff
- **WHEN** un estudiante envía una consulta que coincide con las `palabras_clave` de una entrada en `faqs_jeff`
- **THEN** Jeff retorna la respuesta fija por el canal `JEFF_ADMIN` sin invocar el motor RAG ni el modelo de lenguaje
