export interface Ramo {
  codigo: string;
  nombre: string;
  departamento: string;
  profesor: string;
  descripcion: string;
  documentos: string[];
  reglas_socraticas: string;
}

export type RolUsuario = 'alumno' | 'docente';

export interface Usuario {
  nombre: string;
  rol: RolUsuario;
}

export type CanalChat = 'JEFF_ADMIN' | 'TUTOR_SOCRATICO' | 'FALLBACK_DOCENTE';

export interface EventoMetadataChat {
  canal?: CanalChat;
  puede_escalar?: boolean;
  motivo?: string;
  topico?: string;
  categoria?: string;
}

export interface MensajeChat {
  id: string;
  autor: 'usuario' | 'asistente';
  texto: string;
  hora: string;
  canal?: CanalChat;
  puedeEscalar?: boolean;
  motivoFallback?: string;
  preguntaOriginal?: string;
  estadoEscalamiento?: 'idle' | 'enviando' | 'enviada' | 'error';
}

export interface ConsultaProfesor {
  id: string;
  codigo_ramo: string;
  pregunta: string;
  motivo: string;
  estado: 'pendiente' | 'resuelta' | 'descartada';
  fecha_creacion: string;
  fecha_respuesta?: string | null;
  respuesta_profesor?: string | null;
  guardada_en_jeff: boolean;
  faq_jeff_id?: string | null;
  palabras_clave_sugeridas: string[];
}

export interface ArchivoRecurso {
  nombre: string;
  carpeta: string;
  tamano_bytes: number;
  tamano_legible: string;
  fecha_modificacion: string;
  indexado_rag: boolean;
}

export interface RespuestaArchivos {
  carpetas: string[];
  archivos: ArchivoRecurso[];
}
