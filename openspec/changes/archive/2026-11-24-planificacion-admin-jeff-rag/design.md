# Design

## Context

Las asignaturas pueden tener uno o varios documentos de planificación en distintos formatos (tablas PDF, calendarios, programas en texto o subcarpetas como `Planificacion/Materia` y `Planificacion/Proyecto`). En lugar de imponer un parser de tablas rígido y una pestaña extra para el docente, la arquitectura final utiliza directamente los archivos que el docente sube a `documentos/Planificacion/` (aprovechando el soporte de subcarpetas) combinando entrega directa de documentos a $0 GPU con respaldo RAG informativo.

## Goals / Non-Goals

**Goals:**
- Permitir que el estudiante abra directamente cualquier documento de planificación desde el chat (`GET /api/ramos/{codigo_ramo}/documentos/{ruta:path}`).
- Resolver consultas generales de planificación en Jeff a $0 GPU, ofreciendo botones clicables de desambiguación cuando existen múltiples documentos en `Planificacion/`.
- Responder consultas puntuales de planificación (experiencias, clases, fechas, evaluaciones) mediante RAG informativo sobre `Planificacion/` + `faqs_jeff`, sin bloqueo `fuera_de_foco`, sin retención socrática y adjuntando el enlace al documento fuente.
- Evitar que keywords genéricas de una sola palabra en `faqs_jeff` secuestren ejercicios técnicos/procedimentales.

**Non-Goals:**
- Extraer o editar filas tabulares manualmente en una pestaña dedicada de `DocenteView`.

## Decisions

1. **Descubrimiento dinámico desde `documentos/Planificacion/`:** `router_jeff.listar_documentos_planificacion` recorre `Planificacion/` y sus subcarpetas, generando etiquetas legibles y URLs inline (`/api/ramos/{codigo}/documentos/{ruta}`) sin configuración adicional para el profesor.
2. **Desambiguación clicable en `JEFF_ADMIN`:** Cuando existen 2+ documentos y la consulta es general, `router_jeff` retorna `sugerencias` en el evento SSE `fin`. `ChatWindow.tsx` renderiza estos botones y envía la opción inmediatamente al hacer clic.
3. **RAG informativo priorizado en `Planificacion/` + `faqs_jeff`:** `rag_engine.buscar_fragmentos_planificacion` filtra fragmentos de `Planificacion`, `Planificacion/*` y `faqs_jeff`; `/api/chat` usa un prompt informativo directo y agrega al final el enlace al documento citado.
4. **Guard anti-secuestro en `router_jeff`:** Palabras ≤ 4 letras usan coincidencia exacta/plural (`(?:e?s)?`) y una sola palabra no administrativa no intercepta mensajes con patrones de ejercicio técnico ni preguntas largas sin coincidencia de frase.

## Risks / Trade-offs

- **Nombres de archivo poco descriptivos** → El docente puede organizar en subcarpetas claras dentro de `Planificacion/` (ej. `Planificacion/Proyecto/`) cuyas etiquetas usa Jeff automáticamente.
- **PDFs no indexados aún en ChromaDB** → Si el RAG aún no tiene fragmentos de `Planificacion/`, `/api/chat` responde directamente con los enlaces a los documentos disponibles en `Planificacion/`.
