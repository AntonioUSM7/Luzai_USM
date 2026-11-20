# Spec Delta

## Purpose

Permite que las consultas estudiantiles sin respuesta en Jeff ni en el tutor socrático con RAG sean escaladas explícitamente por el estudiante hacia un buzón docente por ramo, donde el profesor puede responderlas o convertirlas en nuevas FAQs de Jeff.

## ADDED Requirements

### Requirement: Escalamiento confirmado por el estudiante
The system SHALL allow a student to explicitly confirm sending an unanswered query to the course's teacher consultation inbox after a strict fallback response. El estudiante debe confirmar explícitamente el envío de la consulta al buzón del profesor.

#### Scenario: Estudiante confirma envío tras fallback estricto
- **WHEN** el chat entrega una respuesta de fallback estricto con opción de escalamiento y el estudiante confirma el envío
- **THEN** el sistema registra la consulta como pendiente en el buzón del ramo correspondiente y confirma al estudiante que fue enviada

#### Scenario: Consulta no escalada automáticamente
- **WHEN** el chat entrega una respuesta de fallback estricto y el estudiante no confirma el envío
- **THEN** el sistema no crea ningún registro en el buzón docente del ramo

### Requirement: Gestión y conversión a FAQ desde la vista docente
The system SHALL allow teachers to list pending consultations for a course, mark them as resolved or discarded, and optionally save the answer as a new Jeff FAQ entry. El profesor debe poder revisar, responder y convertir consultas en FAQs de Jeff.

#### Scenario: Profesor responde y convierte consulta en FAQ de Jeff
- **WHEN** el profesor responde una consulta pendiente desde la vista docente y selecciona guardarla como FAQ de Jeff con palabras clave asociadas
- **THEN** la consulta pasa a estado resuelta y la nueva entrada queda persistida en la configuración de FAQs de Jeff del ramo para futuras consultas

#### Scenario: Profesor descarta o resuelve sin crear FAQ
- **WHEN** el profesor marca una consulta como resuelta o descartada sin activar la creación de FAQ
- **THEN** el estado de la consulta se actualiza en el buzón del ramo sin modificar las FAQs de Jeff
