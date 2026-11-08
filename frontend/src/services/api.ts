import { Ramo } from '../types';

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
