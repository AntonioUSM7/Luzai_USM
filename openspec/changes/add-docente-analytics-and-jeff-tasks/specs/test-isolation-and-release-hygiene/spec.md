# Spec Delta

## Purpose

Aísla todos los scripts, datos de prueba y residuos de experimentación fuera de los directorios y artefactos del producto final, garantizando que las pruebas automatizadas nunca contaminen los datos operativos de las asignaturas.

## ADDED Requirements

### Requirement: Separación física de scripts y datos de prueba respecto al producto final
The system SHALL place all automated test suites and preserved test fixtures/data in a dedicated top-level test directory outside the production backend and frontend source trees, and SHALL exclude that test directory from container build contexts and production packaging.

#### Scenario: Empaquetado de producción no incluye archivos ni datos de prueba
- **WHEN** se construyen las imágenes o artefactos de despliegue del backend y frontend
- **THEN** los scripts de prueba y los datos/fixtures de prueba quedan excluidos del producto final mientras la suite de pruebas sigue ejecutable desde el directorio dedicado

### Requirement: Limpieza y traslado de residuos de prueba desde los directorios de datos del ramo
The system SHALL keep the course data directories free of synthetic test courses, leftover test uploads, empty legacy image folders, and documents belonging to unrelated course codes, relocating any retained test artifacts to the dedicated test data directory.

#### Scenario: Repositorio operativo solo contiene asignaturas y archivos vigentes
- **WHEN** se inspeccionan los directorios de datos de ramos del producto final
- **THEN** no existen cursos sintéticos de prueba, carpetas residuales de subidas de prueba ni directorios de imágenes vacíos duplicados

### Requirement: Aislamiento de escritura durante la ejecución de pruebas
The system SHALL isolate all filesystem writes performed by automated tests (course configurations, uploaded files, vector collections, teacher escalations, and analytics logs) to temporary directories so running the test suite never creates or modifies files in the operational data directories.

#### Scenario: Ejecución completa de pruebas no ensucia datos operativos ni analíticas
- **WHEN** se ejecuta la suite completa de pruebas automatizadas del backend
- **THEN** no se crean carpetas de cursos de prueba, colecciones vectoriales ni archivos JSONL de analítica dentro de los directorios operativos de datos
