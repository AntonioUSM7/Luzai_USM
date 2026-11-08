# Spec Delta: semantic-router

## Purpose

Permite clasificar e interceptar intenciones de consulta en el servidor web (Jeff) para responder dudas administrativas de asignaturas sin consumir cómputo en el motor de inferencia LLM.

## ADDED Requirements

### Requirement: Interceptación de consultas administrativas
The system SHALL classify queries and respond with preconfigured course FAQ information when matches occur. El sistema debe interceptar consultas administrativas.

#### Scenario: Consulta administrativa reconocida para un ramo
- **WHEN** un estudiante envía una consulta que contiene palabras clave asociadas a fechas o salas de TEL20425
- **THEN** el sistema retorna la respuesta administrativa estática configurada sin invocar el modelo de lenguaje

#### Scenario: Consulta pedagógica no administrativa
- **WHEN** un estudiante envía una consulta de razonamiento técnico o conceptual que no coincide con las preguntas frecuentes
- **THEN** el sistema clasifica la consulta como pedagógica para ser procesada por el orquestador socrático
