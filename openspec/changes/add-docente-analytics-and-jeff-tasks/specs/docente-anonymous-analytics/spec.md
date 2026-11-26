# Spec Delta

## Purpose

Provee un subsistema de analítica anónima por asignatura que registra métricas agregadas sin datos personales, agrupa preguntas equivalentes para visibilizar las dudas más frecuentes y permite al docente monitorear el ahorro entre Jeff y el Tutor Socrático.

## ADDED Requirements

### Requirement: Registro anónimo de consultas por asignatura
The system SHALL record an anonymized event per chat interaction scoped by course code without storing student names, RUTs, email addresses, IP addresses, or session identifiers, and SHALL redact emails, RUTs, URLs, IPv4/IPv6 addresses, and phone numbers from the stored query text before persisting.

#### Scenario: Consulta con datos personales se sanitiza antes de persistir
- **WHEN** un estudiante envía una consulta que incluye un correo electrónico, RUT, dirección IP, número telefónico o URL
- **THEN** el sistema elimina dichos identificadores del texto registrado y persiste el evento únicamente con marca temporal, código de ramo, canal, modo, tópico/motivo opcionales, métricas de latencia/error y el texto sanitizado

#### Scenario: Consulta vacía o solo con espacios no genera evento
- **WHEN** se intenta registrar una consulta sin contenido útil tras la sanitización
- **THEN** el sistema omite la escritura en el registro analítico del ramo

### Requirement: Agrupación de preguntas más frecuentes por tópico y similitud léxica
The system SHALL aggregate recurring student questions in the analytics summary so that equivalent phrasings in the Socratic tutor and teacher fallback channels are grouped together rather than counted only by exact string equality, while Jeff queries group by topic with a readable label.

#### Scenario: Consultas conceptuales parafraseadas se agrupan en una misma pregunta frecuente
- **WHEN** distintos estudiantes consultan variantes equivalentes en el Tutor Socrático o Fallback (por ejemplo *"¿Qué es una VLAN?"*, *"que es vlan"* y *"para que sirve una vlan"*)
- **THEN** el resumen analítico agrupa esas variantes bajo una misma entrada de preguntas frecuentes mostrando el total acumulado, la pregunta representativa y el canal asociado

#### Scenario: Consultas administrativas de Jeff se agrupan por tópico con etiqueta legible
- **WHEN** múltiples consultas activan el mismo tópico de Jeff con distintas redacciones
- **THEN** el resumen analítico consolida el conteo bajo ese tópico mostrando su etiqueta o pregunta representativa en el ranking de dudas frecuentes

#### Scenario: Filtrado de preguntas frecuentes por rango de días y canal
- **WHEN** el cliente consulta el resumen analítico indicando un rango válido de días (1 a 365) y opcionalmente un canal específico
- **THEN** el sistema retorna únicamente los eventos y preguntas frecuentes dentro de esa ventana temporal (y canal si se especificó), o retorna HTTP 400 si el rango está fuera de límite o HTTP 404 si el ramo no existe

### Requirement: Panel docente de analítica anónima y conversión a FAQ de Jeff
The system SHALL display an anonymous analytics dashboard in the teacher workspace with total queries, channel distribution (including a visual comparative breakdown of Jeff vs. Socratic tutor vs. teacher fallback), fallback reasons, daily activity, and the ranked list of most frequent questions with a quick action to save a frequent question as a Jeff FAQ.

#### Scenario: Visualización de métricas comparativas y preguntas más frecuentes
- **WHEN** el docente abre la pestaña de Analítica Anónima de un ramo con historial de consultas
- **THEN** la interfaz muestra los indicadores por canal, una barra/gráfico comparativo de porcentaje de consultas resueltas por Jeff versus Tutor Socrático y Fallback, los motivos de derivación y el listado ordenado de preguntas más frecuentes con su conteo y canal

#### Scenario: Conversión rápida de una duda frecuente en pregunta guardada de Jeff
- **WHEN** el docente selecciona la acción para guardar en Jeff una duda frecuente del Tutor o Fallback
- **THEN** la interfaz abre el formulario de Preguntas Guardadas prellenado con el texto de la pregunta frecuente para que el docente redacte y guarde la respuesta oficial
