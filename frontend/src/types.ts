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

export interface MensajeChat {
  id: string;
  autor: 'usuario' | 'asistente';
  texto: string;
  hora: string;
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
