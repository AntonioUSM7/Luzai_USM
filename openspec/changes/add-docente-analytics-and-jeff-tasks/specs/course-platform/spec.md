# Spec Delta

## ADDED Requirements

### Requirement: Estado real de indexación RAG y reindexación manual en vista docente
The system SHALL reflect each course document's actual `indexado_rag` status in the teacher file explorer and provide a manual reindex action backed by the course's real indexed fragment count.

#### Scenario: Archivo pendiente o no indexado muestra estado real en lugar de etiqueta fija
- **WHEN** el docente visualiza la lista de archivos de un ramo donde un documento aún no tiene fragmentos en la base vectorial
- **THEN** la interfaz distingue visualmente entre archivos indexados y archivos pendientes/no indexados según el valor real devuelto por el backend

#### Scenario: Docente solicita reindexación manual del ramo
- **WHEN** el docente presiona la acción de reindexar en el gestor de archivos del curso
- **THEN** el sistema dispara la reindexación del ramo en segundo plano y permite consultar el conteo actualizado de fragmentos indexados

### Requirement: Consistencia de lista de documentos de ramos en configuración
The system SHALL keep course configuration metadata free of obsolete placeholder document entries that do not exist on disk while deriving active course documents dynamically from the course directory.

#### Scenario: Listado de ramos refleja documentos reales en disco
- **WHEN** el cliente consulta los ramos activos
- **THEN** los documentos reportados por cada ramo corresponden exclusivamente a los archivos indexables reales presentes en su carpeta de documentos
