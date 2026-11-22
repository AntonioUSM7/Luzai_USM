# Spec Delta

## Purpose

Permite configurar por asignatura las reglas socráticas, el estilo de acompañamiento y la extensión de respuesta desde la vista docente, conectando dichas reglas al prompt del tutor generativo local (`qwen3:8b`).

## ADDED Requirements

### Requirement: Configuración pedagógica editable por asignatura
The system SHALL allow teachers to read and update each course's Socratic rules, pedagogical style (`estricto`, `equilibrado`, `paso_a_paso`), and response length (`corta`, `media`) and persist them in the course configuration. El profesor debe poder editar y guardar la configuración socrática del ramo.

#### Scenario: Profesor guarda nueva configuración socrática del ramo
- **WHEN** el profesor actualiza `reglas_socraticas`, `estilo` y `extension` para un ramo desde la vista docente y guarda los cambios
- **THEN** el sistema persiste los nuevos valores en la configuración del ramo y los refleja en las siguientes consultas al tutor socrático

#### Scenario: Valores inválidos de estilo o extensión son rechazados
- **WHEN** un cliente envía un valor de `estilo` o `extension` fuera de los permitidos al endpoint de configuración socrática
- **THEN** el sistema rechaza la solicitud con error de validación sin alterar la configuración existente

### Requirement: Integración de Qwen3 sin latencia de pensamiento oculto
The system SHALL invoke the configured local Ollama LLM (`qwen3:8b` by default) with thinking mode disabled by default while applying the course's Socratic style, length, and custom rules in the system prompt. El sistema debe conectar Qwen3 con streaming directo y reglas del profesor aplicadas.

#### Scenario: Prompt refleja estilo y extensión del ramo
- **WHEN** se construye el prompt del tutor para un ramo con estilo `estricto` y extensión `corta`
- **THEN** el prompt del sistema incluye las instrucciones correspondientes a ese estilo, esa extensión y las `reglas_socraticas` del ramo

#### Scenario: Llamada a Ollama desactiva thinking por defecto
- **WHEN** el backend envía una solicitud de chat en streaming a Ollama con la configuración por defecto
- **THEN** la carga útil incluye el modelo configurado (`qwen3:8b`) con `think: false` para iniciar el streaming de respuesta inmediatamente
