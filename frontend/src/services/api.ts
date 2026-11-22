import {
  Ramo,
  ArchivoRecurso,
  RespuestaArchivos,
  EventoMetadataChat,
  ConsultaProfesor,
  ConfigSocratica,
  FaqJeff,
} from '../types';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Convierte rutas relativas de la API (ej. /api/ramos/.../imagenes/foo.png)
 * en URLs absolutas para que imágenes y enlaces funcionen desde el navegador.
 */
export function resolverUrlApi(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (url.startsWith('/api/')) return `${API_URL}${url}`;
  return url;
}

/**
 * Obtiene la lista de asignaturas activas desde el backend FastAPI.
 */
export async function obtenerRamos(): Promise<Ramo[]> {
  const respuesta = await fetch(`${API_URL}/api/ramos`);
  if (!respuesta.ok) {
    throw new Error('Error al cargar las asignaturas desde el servidor');
  }
  const datos = await respuesta.json();
  return datos.ramos || [];
}

export interface MensajeHistorialApi {
  rol: 'user' | 'assistant';
  contenido: string;
}

/**
 * Envía una consulta de chat al backend y procesa la respuesta en streaming palabra por palabra.
 */
export async function enviarMensajeChat(
  codigoRamo: string,
  mensaje: string,
  onToken: (token: string) => void,
  onMetadata?: (meta: EventoMetadataChat) => void,
  historial: MensajeHistorialApi[] = []
): Promise<void> {
  const respuesta = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      codigo_ramo: codigoRamo,
      mensaje: mensaje.trim(),
      historial: historial.slice(-6),
    }),
  });

  if (!respuesta.ok || !respuesta.body) {
    throw new Error('Error al comunicarse con el backend');
  }

  const lector = respuesta.body.getReader();
  const decodificador = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await lector.read();
    if (done) break;

    buffer += decodificador.decode(value, { stream: true });
    const lineas = buffer.split('\n\n');
    buffer = lineas.pop() || '';

    for (const bloque of lineas) {
      if (bloque.startsWith('data: ')) {
        const jsonStr = bloque.replace('data: ', '').trim();
        try {
          const evento = JSON.parse(jsonStr);
          if (evento.tipo === 'token' && evento.contenido) {
            onToken(evento.contenido);
          } else if ((evento.tipo === 'inicio' || evento.tipo === 'fin') && onMetadata) {
            onMetadata({
              canal: evento.canal,
              puede_escalar: evento.puede_escalar,
              motivo: evento.motivo,
              topico: evento.topico,
              categoria: evento.categoria,
            });
          }
        } catch {
          // Ignorar bloques no JSON
        }
      }
    }
  }
}

/**
 * Crea una nueva carpeta en el repositorio de documentos del ramo.
 */
export async function crearCarpetaRamo(codigoRamo: string, nombre: string): Promise<string> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/carpetas`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre }),
  });

  if (!respuesta.ok) {
    throw new Error('Error al crear la carpeta');
  }

  const datos = await respuesta.json();
  return datos.nombre;
}

/**
 * Elimina una carpeta y su contenido de un ramo.
 */
export async function eliminarCarpetaRamo(
  codigoRamo: string,
  nombreCarpeta: string
): Promise<void> {
  const params = new URLSearchParams({
    nombre_carpeta: nombreCarpeta,
  });

  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/carpetas?${params.toString()}`, {
    method: 'DELETE',
  });

  if (!respuesta.ok) {
    throw new Error('Error al eliminar la carpeta');
  }
}

/**
 * Obtiene la lista de archivos de un ramo organizados por carpeta.
 */
export async function listarArchivosRamo(codigoRamo: string): Promise<RespuestaArchivos> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/archivos`);
  if (!respuesta.ok) {
    throw new Error('Error al cargar los archivos del ramo');
  }
  const datos = await respuesta.json();
  return {
    carpetas: datos.carpetas || [],
    archivos: datos.archivos || [],
  };
}

/**
 * Sube un archivo a una carpeta específica del ramo.
 */
export async function subirArchivoRamo(
  codigoRamo: string,
  archivo: File,
  carpeta: string
): Promise<ArchivoRecurso> {
  const formData = new FormData();
  formData.append('archivo', archivo);
  formData.append('carpeta', carpeta);

  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/archivos`, {
    method: 'POST',
    body: formData,
  });

  if (!respuesta.ok) {
    throw new Error('Error al subir el archivo');
  }

  const datos = await respuesta.json();
  return datos.archivo;
}

/**
 * Elimina un archivo de una carpeta de un ramo.
 */
export async function eliminarArchivoRamo(
  codigoRamo: string,
  carpeta: string,
  nombreArchivo: string
): Promise<void> {
  const params = new URLSearchParams({
    carpeta,
    nombre_archivo: nombreArchivo,
  });

  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/archivos?${params.toString()}`, {
    method: 'DELETE',
  });

  if (!respuesta.ok) {
    throw new Error('Error al eliminar el archivo');
  }
}

/**
 * Envía una consulta sin respuesta al buzón del profesor del ramo (previa confirmación del alumno).
 */
export async function enviarConsultaProfesor(
  codigoRamo: string,
  pregunta: string,
  motivo = 'sin_respaldo_rag'
): Promise<ConsultaProfesor> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/consultas`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pregunta, motivo }),
  });

  if (!respuesta.ok) {
    throw new Error('Error al enviar la consulta al profesor');
  }

  const datos = await respuesta.json();
  return datos.consulta;
}

/**
 * Lista las consultas escaladas al profesor para un ramo.
 */
export async function listarConsultasProfesor(
  codigoRamo: string,
  estado?: 'pendiente' | 'resuelta' | 'descartada'
): Promise<ConsultaProfesor[]> {
  const query = estado ? `?estado=${encodeURIComponent(estado)}` : '';
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/consultas${query}`);

  if (!respuesta.ok) {
    throw new Error('Error al cargar las consultas del profesor');
  }

  const datos = await respuesta.json();
  return datos.consultas || [];
}

/**
 * Responde o descarta una consulta desde la vista docente y opcionalmente la guarda como FAQ de Jeff.
 */
export async function responderConsultaProfesor(
  codigoRamo: string,
  consultaId: string,
  payload: {
    estado: 'resuelta' | 'descartada';
    respuesta_profesor?: string;
    guardar_en_jeff?: boolean;
    categoria?: string;
    palabras_clave?: string[];
  }
): Promise<{ consulta: ConsultaProfesor; faq_creada?: Record<string, unknown> | null }> {
  const respuesta = await fetch(
    `${API_URL}/api/ramos/${codigoRamo}/consultas/${encodeURIComponent(consultaId)}/responder`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  );

  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({}));
    throw new Error(detalle.detail || 'Error al actualizar la consulta');
  }

  return respuesta.json();
}

/**
 * Obtiene la configuración socrática editable de un ramo.
 */
export async function obtenerConfigSocratica(codigoRamo: string): Promise<ConfigSocratica> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/config_socratica`);
  if (!respuesta.ok) {
    throw new Error('Error al cargar la configuración socrática del ramo');
  }
  return respuesta.json();
}

/**
 * Actualiza las reglas socráticas, estilo y extensión del tutor para un ramo.
 */
export async function actualizarConfigSocratica(
  codigoRamo: string,
  payload: Pick<ConfigSocratica, 'reglas_socraticas' | 'estilo' | 'extension'>
): Promise<ConfigSocratica> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/config_socratica`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({}));
    throw new Error(detalle.detail || 'Error al guardar la configuración socrática');
  }

  return respuesta.json();
}

export interface FaqJeffPayload {
  pregunta?: string;
  respuesta: string;
  palabras_clave?: string[];
  categoria?: string;
}

/**
 * Lista las preguntas guardadas de Jeff para un ramo.
 */
export async function listarFaqsJeff(codigoRamo: string): Promise<FaqJeff[]> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/faqs_jeff`);
  if (!respuesta.ok) {
    throw new Error('Error al cargar las preguntas guardadas de Jeff');
  }
  const datos = await respuesta.json();
  return datos.faqs || [];
}

/**
 * Crea una nueva pregunta guardada de Jeff (y la sincroniza con RAG).
 */
export async function crearFaqJeff(
  codigoRamo: string,
  payload: FaqJeffPayload
): Promise<{ faq: FaqJeff; rag_sincronizado: boolean }> {
  const respuesta = await fetch(`${API_URL}/api/ramos/${codigoRamo}/faqs_jeff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({}));
    throw new Error(detalle.detail || 'Error al guardar la pregunta en Jeff');
  }
  return respuesta.json();
}

/**
 * Actualiza una pregunta guardada de Jeff existente (y la re-indexa en RAG).
 */
export async function actualizarFaqJeff(
  codigoRamo: string,
  faqId: string,
  payload: FaqJeffPayload
): Promise<{ faq: FaqJeff; rag_sincronizado: boolean }> {
  const respuesta = await fetch(
    `${API_URL}/api/ramos/${codigoRamo}/faqs_jeff/${encodeURIComponent(faqId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  );
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({}));
    throw new Error(detalle.detail || 'Error al actualizar la pregunta de Jeff');
  }
  return respuesta.json();
}

/**
 * Elimina una pregunta guardada de Jeff (y su vector asociado en RAG).
 */
export async function eliminarFaqJeff(
  codigoRamo: string,
  faqId: string
): Promise<{ faq: FaqJeff; rag_sincronizado: boolean }> {
  const respuesta = await fetch(
    `${API_URL}/api/ramos/${codigoRamo}/faqs_jeff/${encodeURIComponent(faqId)}`,
    {
      method: 'DELETE',
    }
  );
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({}));
    throw new Error(detalle.detail || 'Error al eliminar la pregunta de Jeff');
  }
  return respuesta.json();
}
