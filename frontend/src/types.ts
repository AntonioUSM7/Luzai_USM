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
