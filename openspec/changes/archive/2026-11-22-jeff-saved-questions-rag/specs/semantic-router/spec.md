# Spec Delta

## ADDED Requirements

### Requirement: Persistencia de pregunta original y respaldo dual en FAQs de Jeff
The system SHALL preserve the original `pregunta` text when saving a teacher-resolved query into `faqs_jeff` and maintain deterministic keyword interception at zero GPU cost alongside vector synchronization for the Socratic tutor.

#### Scenario: Escalación resuelta guardada en Jeff conserva la pregunta original
- **WHEN** el docente resuelve una consulta escalada marcando la opción de guardar en Jeff
- **THEN** la entrada creada en `faqs_jeff` incluye la `pregunta` original de la consulta además de `palabras_clave`, `categoria` y `respuesta`, quedando disponible tanto para coincidencia por palabras clave en Jeff como para recuperación semántica en RAG

#### Scenario: Coincidencia exacta por palabras clave mantiene prioridad en Jeff
- **WHEN** un estudiante envía una consulta que coincide con las `palabras_clave` de una entrada en `faqs_jeff`
- **THEN** Jeff retorna la respuesta fija por el canal `JEFF_ADMIN` sin invocar el motor RAG ni el modelo de lenguaje
