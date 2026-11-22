# Spec Delta

## ADDED Requirements

### Requirement: Fallback estricto sin respaldo en Jeff ni RAG
The system SHALL return a deterministic strict fallback response without invoking the language model when a non-greeting query matches neither Jeff's administrative FAQs nor sufficient RAG course context. El sistema debe responder con fallback estricto a costo cero de GPU cuando no exista respaldo suficiente.

#### Scenario: Consulta académica sin respaldo en apuntes ni Jeff
- **WHEN** un estudiante envía una consulta que no es saludo, no coincide con las FAQs de Jeff y no alcanza el umbral de contexto RAG ni cobertura en el temario configurado
- **THEN** el sistema omite la invocación al modelo de lenguaje, emite el mensaje de fallback estricto configurado para el ramo por el canal `FALLBACK_DOCENTE` y habilita la opción de escalar al profesor

#### Scenario: Consulta administrativa desconocida por Jeff
- **WHEN** un estudiante envía una consulta administrativa que no coincide con ninguna FAQ configurada en el ramo y no obtiene respaldo RAG suficiente
- **THEN** el sistema responde por el canal `FALLBACK_DOCENTE` sin invocar al modelo de lenguaje y ofrece escalar la consulta al profesor
