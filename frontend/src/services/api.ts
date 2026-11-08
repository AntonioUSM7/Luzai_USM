import { Ramo, ArchivoRecurso, RespuestaArchivos } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

/**
 * Envía una consulta de chat al backend y procesa la respuesta en streaming palabra por palabra.
 */
export async function enviarMensajeChat(
  codigoRamo: string,
  mensaje: string,
  onToken: (token: string) => void
): Promise<void> {
  const respuesta = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      codigo_ramo: codigoRamo,
      mensaje: mensaje.trim(),
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
