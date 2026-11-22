# Spec Delta

## Purpose

Provee un repositorio administrable por el docente de preguntas y respuestas guardadas por asignatura, sincronizado con la base vectorial del curso para que el Tutor Socrático pueda recuperarlas semánticamente como respaldo oficial.

## ADDED Requirements

### Requirement: Gestión CRUD de preguntas guardadas por asignatura
The system SHALL allow teachers to list, create, update, and delete saved questions (`faqs_jeff`) for a course, storing `id`, `categoria`, `palabras_clave`, `respuesta`, and optional `pregunta`.

#### Scenario: Crear una nueva pregunta guardada desde el panel docente
- **WHEN** el docente envía una nueva pregunta guardada con palabras clave y respuesta válidas para un ramo existente
- **THEN** el sistema persiste la entrada de forma atómica en `config.json` del ramo y retorna la entrada creada con su identificador

#### Scenario: Editar o eliminar una pregunta guardada existente
- **WHEN** el docente actualiza o elimina una pregunta guardada por su identificador
- **THEN** el sistema refleja el cambio en `config.json` del ramo o retorna HTTP 404 si el identificador no existe

### Requirement: Sincronización de preguntas guardadas con el índice vectorial del ramo
The system SHALL index saved questions and their answers into the course vector store upon creation, update, escalation-to-Jeff, and full course reindexing, and remove them upon deletion.

#### Scenario: Indexación automática al guardar o actualizar una pregunta
- **WHEN** se crea o actualiza una pregunta guardada (directamente o al resolver una consulta escalada con guardado en Jeff)
- **THEN** el sistema genera o actualiza su documento en la colección vectorial del ramo combinando pregunta, categoría y respuesta

#### Scenario: Eliminación del índice vectorial al borrar una pregunta
- **WHEN** se elimina una pregunta guardada del ramo
- **THEN** el sistema elimina su vector asociado en la colección vectorial del ramo sin afectar los apuntes PDF indexados

### Requirement: Recuperación semántica de preguntas guardadas por el Tutor Socrático
The system SHALL retrieve relevant saved questions from the course vector store during pedagogical chat queries when Jeff does not intercept by keywords, preventing false lack-of-context fallbacks.

#### Scenario: Consulta parafraseada sin coincidencia exacta de palabras clave en Jeff
- **WHEN** un estudiante realiza una pregunta semánticamente equivalente a una pregunta guardada usando palabras distintas a sus `palabras_clave`
- **THEN** Jeff no intercepta la consulta y el motor RAG recupera la pregunta guardada como contexto oficial para que el Tutor Socrático responda fundamentado en ella

### Requirement: Apartado de Preguntas Guardadas en la vista docente
The system SHALL provide a management UI in the teacher view's Jeff tab to search, create, edit, and delete saved questions for the selected course.

#### Scenario: Visualización y edición de preguntas en la pestaña Jeff
- **WHEN** el docente abre la sub-pestaña Jeff de un ramo
- **THEN** la interfaz muestra el listado de preguntas guardadas con filtro de búsqueda y acciones para crear, editar y eliminar entradas
