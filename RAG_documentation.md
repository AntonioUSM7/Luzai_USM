# Guía Técnica de Implementación del Motor RAG - LuzAI USM
**Documento para el Técnico:** Ahmaru  
**Proyecto:** LuzAI USM - Tutor Socrático Inteligente  
**Entorno de Hardware recomendado:** CPU AMD Ryzen 7 3700X, 16 GB RAM, GPU NVIDIA GTX 1660 Ti (6 GB VRAM).

UWU ahora voy a desarrollar esto en una branch mas uwur u know what i mean

---

## 1. Visión General del RAG en LuzAI

El motor **RAG (Retrieval-Augmented Generation)** permite que el modelo de lenguaje (**Qwen 3.8 8B / Qwen 2.5**) responda dudas académicas basándose estrictamente en los apuntes, guías y certámenes oficiales cargados por los profesores en la plataforma, evitando alucinaciones y garantizando el andamiaje socrático.

```text
[Profesor sube PDF vía Web]
           │
           ▼
[backend/data/ramos/{CODIGO}/documentos/{Carpeta}/]
           │
           ├── 1. Extracción de texto (pypdf / pymupdf)
           ├── 2. Chunking (fragmentos de 500-800 caracteres con overlap)
           ├── 3. Embeddings locales (Ollama: nomic-embed-text)
           └── 4. Base Vectorial Local (ChromaDB en backend/data/ramos/{CODIGO}/chroma/)
                                      │
[Alumno pregunta en el Chat] ─────────┼── 5. Búsqueda por similitud semántica (Top-K)
                                      ▼
                      [Contexto inyectado en System Prompt]
                                      │
                                      ▼
                            [Qwen: Pistas Socráticas]
```

---

## 2. Modelos en Ollama y Consumo de Hardware

Para que el pipeline vuele en tu **GTX 1660 Ti (6 GB VRAM)** sin saturar memoria:

### A. Modelo de Embeddings (Cero consumo de VRAM)
Utilizamos **`nomic-embed-text`**:
* Tamaño en disco: **~274 MB**.
* Consumo de VRAM: **< 300 MB** (o puede correr en CPU en milisegundos).
* Comando para descargarlo:
  ```bash
  ollama pull nomic-embed-text
  ```

### B. Modelo LLM para Desarrollo y Pruebas
Para probar respuestas locales mientras desarrollas el RAG:
* **`qwen2.5:3b`** (~2.0 GB VRAM): Ultra rápido para pruebas de integración.
* **`qwen2.5:7b`** (Q4_K_M, ~4.5 GB VRAM): Para pruebas de calidad de razonamiento en tu máquina.
* Comando:
  ```bash
  ollama pull qwen2.5:3b
  ```

---

## 3. Estructura de Directorios y Persistencia

El frontend y el backend ya organizan los archivos por ramo y por carpeta en la siguiente ruta:

```text
backend/data/ramos/
├── MAT024/
│   ├── config.json                 # Metadatos del ramo, tareas y FAQs de Jeff
│   ├── documentos/                 # PDFs físicos subidos por el profesor
│   │   ├── Clases/                 # Apuntes y diapositivas teóricas
│   │   ├── Guias/                  # Guías de ejercicios prácticos
│   │   ├── Tareas/                 # Enunciados y pautas
│   │   └── Certamenes/             # Evaluaciones pasadas
│   └── chroma/                     # 📁 AQUÍ SE GUARDA LA BASE VECTORIAL
│       └── chroma.sqlite3          # Persistencia automática de ChromaDB
└── TEL20425/
    ├── config.json
    ├── documentos/
    └── chroma/
```

---

## 4. Dependencias de Python Necesarias

Para implementar el RAG en `backend/requirements.txt`, se deben agregar:

```txt
chromadb>=0.5.0
pypdf>=4.0.0
pymupdf4llm>=0.0.17
```

Para instalarlas en el entorno de desarrollo:
```bash
pip install chromadb pypdf pymupdf4llm
# o dentro del contenedor:
docker compose exec backend pip install chromadb pypdf pymupdf4llm
```

---

## 5. Arquitectura del Archivo `backend/rag_engine.py`

Crea el archivo `backend/rag_engine.py`. A continuación se proporciona una plantilla base modular lista para conectar:

```python
import os
from pathlib import Path
from typing import List, Dict, Any
import httpx
import chromadb
from chromadb.config import Settings
from pypdf import PdfReader

# Configuración de rutas y Ollama
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "ramos"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"


def obtener_cliente_chroma(codigo_ramo: str):
    """Inicializa o carga la base vectorial persistente para el ramo"""
    ruta_chroma = DATA_DIR / codigo_ramo.upper() / "chroma"
    ruta_chroma.mkdir(parents=True, exist_ok=True)
    
    cliente = chromadb.PersistentClient(path=str(ruta_chroma))
    coleccion = cliente.get_or_create_collection(
        name=f"luzai_{codigo_ramo.lower()}",
        metadata={"hnsw:space": "cosine"}
    )
    return coleccion


def generar_embedding_ollama(texto: str) -> List[float]:
    """Genera el vector embedding usando nomic-embed-text en Ollama"""
    url = f"{OLLAMA_HOST}/api/embeddings"
    payload = {"model": EMBEDDING_MODEL, "prompt": texto}
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["embedding"]


def extraer_texto_pdf(ruta_pdf: Path) -> List[Dict[str, Any]]:
    """Extrae texto página por página de un PDF"""
    paginas = []
    lector = PdfReader(str(ruta_pdf))
    for i, pag in enumerate(lector.pages):
        contenido = pag.extract_text() or ""
        if contenido.strip():
            paginas.append({"pagina": i + 1, "texto": contenido.strip()})
    return paginas


def crear_chunks(texto: str, max_caracteres: int = 700, overlap: int = 100) -> List[str]:
    """Divide un texto largo en fragmentos manejables con solapamiento"""
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + max_caracteres
        chunks.append(texto[inicio:fin])
        inicio += (max_caracteres - overlap)
    return chunks


# ============================================================================
# FUNCIONES PRINCIPALES QUE LLAMA EL BACKEND (app.py)
# ============================================================================

def indexar_documento(ruta_archivo: Path, codigo_ramo: str, carpeta: str) -> Dict[str, Any]:
    """
    Lee un PDF subido por el profesor, lo fragmenta, calcula embeddings
    y lo almacena en la colección vectorial del ramo.
    """
    coleccion = obtener_cliente_chroma(codigo_ramo)
    paginas = extraer_texto_pdf(ruta_archivo)
    
    total_chunks = 0
    for pag in paginas:
        fragmentos = crear_chunks(pag["texto"])
        for idx, frag in enumerate(fragmentos):
            vector = generar_embedding_ollama(frag)
            doc_id = f"{ruta_archivo.name}_p{pag['pagina']}_c{idx}"
            
            coleccion.upsert(
                ids=[doc_id],
                embeddings=[vector],
                documents=[frag],
                metadatas=[{
                    "archivo": ruta_archivo.name,
                    "carpeta": carpeta,
                    "pagina": pag["pagina"],
                    "codigo_ramo": codigo_ramo.upper()
                }]
            )
            total_chunks += 1

    return {
        "status": "ok",
        "archivo": ruta_archivo.name,
        "chunks_indexados": total_chunks
    }


def eliminar_documento_vectorial(nombre_archivo: str, codigo_ramo: str, carpeta: str):
    """Elimina de ChromaDB todos los fragmentos asociados a un archivo borrado"""
    coleccion = obtener_cliente_chroma(codigo_ramo)
    coleccion.delete(where={"archivo": nombre_archivo})


def buscar_contexto_relevante(query: str, codigo_ramo: str, top_k: int = 3) -> str:
    """
    Busca los fragmentos más cercanos a la duda del alumno para inyectar al LLM.
    """
    coleccion = obtener_cliente_chroma(codigo_ramo)
    if coleccion.count() == 0:
        return ""

    vector_query = generar_embedding_ollama(query)
    resultados = coleccion.query(
        query_embeddings=[vector_query],
        n_results=min(top_k, coleccion.count())
    )

    documentos = resultados.get("documents", [[]])[0]
    return "\n---\n".join(documentos)
```

---

## 6. Puntos de Conexión en `backend/app.py`

Una vez que tengas listo `backend/rag_engine.py`, en `app.py` solo se conectan estas dos líneas:

### 1. En la subida de archivos (`POST /api/ramos/{codigo_ramo}/archivos`):
```python
import rag_engine

# Después de guardar el archivo físicamente en disco:
resultado_rag = rag_engine.indexar_documento(ruta_archivo, codigo, carpeta_limpia)
print(f"RAG Indexado: {resultado_rag['chunks_indexados']} fragmentos generados.")
```

### 2. En la eliminación de archivos (`DELETE /api/ramos/{codigo_ramo}/archivos`):
```python
# Al borrar el archivo de disco:
rag_engine.eliminar_documento_vectorial(nombre_archivo, codigo, carpeta)
```

### 3. En la consulta de chat de los alumnos (`POST /api/chat`):
```python
# Antes de llamar al LLM:
contexto_apuntes = rag_engine.buscar_contexto_relevante(consulta.mensaje, consulta.codigo_ramo)

system_prompt = f"""
Eres LuzAI, tutor socrático institucional para la asignatura {consulta.codigo_ramo}.
Utiliza el siguiente contexto de apuntes oficiales para formular tus pistas y preguntas guía:
{contexto_apuntes}

REGLA DE ORO: Jamás entregues la solución completa ni resuelvas el ejercicio. Guía con preguntas.
"""
```

---

## 7. Pruebas Rápidas Recomendadas para Ahmaru

1. Iniciar Ollama y asegurar que el modelo de embeddings esté listo:
   ```bash
   ollama run nomic-embed-text
   ```
2. Crear un archivo de prueba `test_rag.py` para verificar que extrae y busca:
   ```python
   from rag_engine import indexar_documento, buscar_contexto_relevante
   from pathlib import Path

   # Probar con un PDF de prueba de MAT024:
   # indexar_documento(Path("data/ramos/MAT024/documentos/Clases/ejemplo.pdf"), "MAT024", "Clases")
   # contexto = buscar_contexto_relevante("¿Cómo se calcula la integral de superficie?", "MAT024")
   # print("Contexto recuperado:\n", contexto)
   ```
3. ¡Listo! Cualquier ajuste de latencia o tamaño de chunk se puede calibrar directamente en `rag_engine.py`.

---

## 8. Optimización Avanzada: Conversión a Markdown + LaTeX (`pymupdf4llm`)

Para asignaturas de ingeniería y ciencias con alta densidad de fórmulas (ej. `MAT024` con cálculo/EDPs o `TEL20425` con fórmulas de telecomunicaciones), el texto plano de `pypdf` suele romper la sintaxis matemática.

### ¿Por qué convertir el PDF a Markdown + LaTeX?
1. **Preservación Matemática:** Las integrales, sumatorias y matrices se convierten a código KaTeX nativo (`\int_{0}^{\pi} \sin(x) dx`, `\nabla \cdot \vec{E}`), que **Qwen entiende y razona a la perfección**.
2. **Ahorro de hasta un 50% de Tokens:** El Markdown elimina encabezados repetitivos, números de página y saltos de línea rotos. Menos tokens = **menor consumo de memoria VRAM (KV Cache) en tu GPU de 6 GB**.
3. **Estructura Semántica:** Los títulos (`#`, `##`), listas y tablas permanecen estructurados, permitiendo que el chunking no corte teoremas por la mitad.

### Implementación con `pymupdf4llm`:
```python
import pymupdf4llm

def extraer_markdown_con_latex(ruta_pdf: Path, ruta_imagenes: Path = None) -> str:
    """
    Convierte el PDF a Markdown estructurado con soporte de LaTeX y tablas.
    Opcionalmente extrae las imágenes a una carpeta designada.
    """
    md_text = pymupdf4llm.to_markdown(
        doc=str(ruta_pdf),
        write_images=True if ruta_imagenes else False,
        image_path=str(ruta_imagenes) if ruta_imagenes else None
    )
    return md_text
```

---

## 9. Gestión Ligera de Imágenes y Diagramas Técnicos

En asignaturas técnicas, los diagramas de redes, circuitos y gráficos 3D son indispensables. Sin embargo, procesar imágenes con modelos de visión multimodales pesados (VLM como LLaVA o Qwen-VL) en tiempo real consumiría demasiada VRAM (~1.500 tokens por imagen) y saturaría la GTX 1660 Ti.

### Estrategia Ligera Recomendada (Costo $0 y Cero Impacto en VRAM):
1. **Extracción Automática de Imágenes:**
   * Al procesar el PDF, `pymupdf4llm` extrae las figuras a la subcarpeta:
     `backend/data/ramos/{CODIGO}/imagenes/`
   * En el Markdown generado, deja la referencia al archivo:
     ```markdown
     ![Diagrama de Red](/api/ramos/TEL20425/imagenes/figura_topologia_anillo.png)
     *Figura 2: Topología de red en anillo con enlaces redundantes.*
     ```

2. **Indexación de Pies de Foto (Captions):**
   * El RAG vectoriza el texto descriptivo de la imagen (*"Figura 2: Topología de red en anillo..."*).
   * Cuando el alumno pregunta por *"¿Cómo funciona la topología en anillo?"*, el RAG recupera el fragmento con la ruta de la imagen.

3. **Despliegue Visual en el Chat (Frontend):**
   * El componente de chat de React renderiza el Markdown del tutor, desplegando la imagen directamente en la conversación del estudiante.
   * El tutor socrático puede guiar al alumno haciendo referencia visual a la imagen:
     > *"Revisa el diagrama que te adjunto arriba. Si el enlace entre el Router A y B se corta, ¿por cuál ruta alternativa circularán los paquetes según la topología?"*
