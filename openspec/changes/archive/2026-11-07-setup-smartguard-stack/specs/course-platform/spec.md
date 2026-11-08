# Spec Delta: course-platform

## Purpose

Provee la plataforma de gestión y consulta de asignaturas simuladas de AULA USM, permitiendo a los clientes web acceder a metadatos de los ramos, recursos de apoyo y verificar la salud de los servicios.

## ADDED Requirements

### Requirement: Consulta de asignaturas disponibles
The system SHALL expose an endpoint to list simulated academic courses available for students and teachers. El sistema debe listar las asignaturas disponibles.

#### Scenario: Listar asignaturas activas exitosamente
- **WHEN** el cliente solicita la lista de asignaturas activas
- **THEN** el sistema retorna el listado de ramos incluyendo TEL20425 y MAT024 con sus nombres oficiales y códigos respectivos

### Requirement: Verificación del estado de salud del sistema
The system SHALL provide a diagnostic health-check endpoint to verify availability of backend services. El sistema debe responder sobre la salud de los servicios.

#### Scenario: Diagnóstico exitoso de servicios
- **WHEN** se envía una solicitud de verificación de salud al backend
- **THEN** el sistema responde con estado HTTP 200 y confirmación operativa del servicio
