# Spec Delta

## ADDED Requirements

### Requirement: Protección contra secuestro de ejercicios técnicos por palabras clave genéricas en Jeff
The system SHALL avoid intercepting technical or procedural student exercises when a Jeff FAQ only matches an isolated generic keyword without a multi-word phrase match, and SHALL restrict short keywords (4 characters or fewer) to exact or simple plural word matches.

#### Scenario: Ejercicio técnico que menciona una palabra genérica pasa al Tutor Socrático
- **WHEN** un estudiante envía un ejercicio técnico o de cálculo (ej. *"si quiero una red 10 host, que mascara deberia usar"*) y una FAQ de Jeff solo coincide en una palabra suelta no administrativa (ej. *"red"*)
- **THEN** Jeff no intercepta la consulta y la deriva al orquestador del Tutor Socrático

#### Scenario: Pregunta directa por frase clave sigue respondiendo en Jeff a $0 GPU
- **WHEN** un estudiante envía una consulta que coincide con una frase clave configurada en `faqs_jeff` (ej. *"¿qué es una red?"*)
- **THEN** Jeff responde de inmediato por el canal `JEFF_ADMIN` a $0 GPU
