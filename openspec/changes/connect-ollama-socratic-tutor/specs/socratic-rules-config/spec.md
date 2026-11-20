# socratic-rules-config Specification

## Purpose

Permite a los docentes consultar, editar y persistir las reglas socráticas específicas de cada asignatura desde la interfaz web, actualizando la configuración local del ramo consumida por el tutor.

## ADDED Requirements

### Requirement: Actualización y persistencia de reglas socráticas del ramo
El sistema SHALL exponer un endpoint para actualizar el campo `reglas_socraticas` en el archivo `config.json` de una asignatura existente, validando que el contenido no esté vacío y preservando los demás campos de configuración.

#### Scenario: Guardado exitoso de reglas socráticas
- **WHEN** un cliente envía nuevas `reglas_socraticas` válidas para una asignatura existente
- **THEN** el sistema actualiza `config.json` preservando metadatos, documentos y `faqs_jeff`, y retorna la configuración actualizada con estado HTTP 200

#### Scenario: Reglas vacías o asignatura inexistente
- **WHEN** se intenta guardar `reglas_socraticas` vacías o para un código de asignatura inexistente
- **THEN** el sistema rechaza la solicitud con estado HTTP 400 o 404 según corresponda

### Requirement: Editor docente de reglas socráticas en interfaz web
La vista docente SHALL ofrecer en la pestaña "Reglas Socráticas" un editor conectado al backend para visualizar las reglas actuales del ramo, modificarlas y guardar cambios con confirmación visual.

#### Scenario: Edición y guardado desde la vista docente
- **WHEN** el docente edita el texto de reglas socráticas del ramo activo y presiona guardar
- **THEN** la interfaz envía los cambios al backend, actualiza el estado local del ramo y muestra confirmación de guardado sin perder el contexto de la vista
