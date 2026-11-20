# socratic-tutor Specification

## Purpose

Provee la orquestación de tutoría socrática en tiempo real mediante streaming SSE conectado al motor local Ollama, aplicando las reglas pedagógicas institucionales y específicas de cada asignatura sin entregar respuestas resueltas.

## ADDED Requirements

### Requirement: Respuesta socrática en streaming vía Ollama
El sistema SHALL procesar consultas pedagógicas en el endpoint de chat conectándose al motor local Ollama y transmitiendo la respuesta en tiempo real mediante Server-Sent Events (SSE) con eventos de token y finalización.

#### Scenario: Consulta pedagógica respondida en streaming
- **WHEN** un estudiante envía una consulta válida para una asignatura existente y Ollama está disponible
- **THEN** el sistema consulta a Ollama en modo streaming y emite eventos SSE `token` progresivos seguidos de un evento `fin`

#### Scenario: Asignatura inexistente en consulta de chat
- **WHEN** un cliente envía una consulta indicando un código de asignatura que no existe
- **THEN** el sistema rechaza la solicitud con estado HTTP 404

### Requirement: Ensamblaje de System Prompt socrático y guardrails
El sistema SHALL construir un System Prompt por cada consulta combinando las reglas institucionales de andamiaje cognitivo (prohibición de entregar soluciones completas o código resuelto y resistencia a manipulación de instrucciones) con las `reglas_socraticas` configuradas para la asignatura.

#### Scenario: Inyección de reglas específicas del ramo
- **WHEN** un estudiante consulta sobre una asignatura que tiene `reglas_socraticas` definidas
- **THEN** el System Prompt enviado al modelo incluye tanto las restricciones institucionales base como las reglas específicas de esa asignatura

#### Scenario: Intento de salto de reglas (Prompt Injection)
- **WHEN** un estudiante solicita explícitamente ignorar las instrucciones previas y entregar la respuesta o código completo
- **THEN** el System Prompt instruye al modelo a mantener el rol socrático y responder únicamente con pistas o preguntas guía

### Requirement: Contexto conversacional efímero de sesión
El sistema SHALL aceptar un historial opcional de mensajes previos de la sesión actual para mantener continuidad socrática multi-turno, sin almacenar identidad del estudiante ni persistir conversaciones en disco.

#### Scenario: Consulta con historial de sesión
- **WHEN** el cliente envía una consulta acompañada del historial reciente de mensajes usuario-asistente
- **THEN** el sistema incluye ese historial en la secuencia de mensajes enviada a Ollama manteniendo el System Prompt al inicio

### Requirement: Manejo de indisponibilidad de Ollama
El sistema SHALL informar de manera controlada cuando el servicio Ollama no esté accesible o el modelo configurado no esté disponible, sin bloquear indefinidamente la interfaz del estudiante.

#### Scenario: Ollama no disponible o modelo faltante
- **WHEN** el backend no logra conectarse a Ollama o recibe un error del motor de inferencia
- **THEN** el sistema emite un mensaje de error legible por el canal de chat y finaliza el stream limpiamente para que el usuario pueda reintentar
