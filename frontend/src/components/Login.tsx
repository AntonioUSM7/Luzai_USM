import React, { useState } from 'react';
import { RolUsuario, Usuario } from '../types';
import { GraduationCap, UserCheck, LogIn } from 'lucide-react';
import logoUsm from '../resources/marca-color.png';

interface LoginProps {
  onLogin: (usuario: Usuario) => void;
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [nombre, setNombre] = useState('');
  const [rol, setRol] = useState<RolUsuario>('alumno');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const nombreFinal = nombre.trim() || (rol === 'alumno' ? 'Estudiante USM' : 'Profesor USM');
    onLogin({ nombre: nombreFinal, rol });
  };

  return (
    <div className="min-h-screen w-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-sm p-8">
        <div className="text-center mb-6">
          <img
            src={logoUsm}
            alt="Logo USM"
            className="h-12 mx-auto mb-4 object-contain"
          />
          <h1 className="text-2xl font-bold text-slate-800">LuzAI USM</h1>
          <p className="text-sm text-slate-500 mt-1">Plataforma Académica Institucional</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase text-slate-600 mb-2">
              Selecciona tu Perfil
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setRol('alumno')}
                className={`py-3 px-3 rounded-xl border flex flex-col items-center gap-1.5 transition text-xs font-medium ${
                  rol === 'alumno'
                    ? 'border-usm-blue bg-usm-blue text-white shadow-sm'
                    : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <GraduationCap className="w-5 h-5" />
                Estudiante
              </button>

              <button
                type="button"
                onClick={() => setRol('docente')}
                className={`py-3 px-3 rounded-xl border flex flex-col items-center gap-1.5 transition text-xs font-medium ${
                  rol === 'docente'
                    ? 'border-usm-blue bg-usm-blue text-white shadow-sm'
                    : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <UserCheck className="w-5 h-5" />
                Docente
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-600 mb-1">
              Nombre o Correo Institucional
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder={rol === 'alumno' ? 'ej: antonio.alumno@usm.cl' : 'ej: profesor.redes@usm.cl'}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-usm-blue"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-usm-blue hover:bg-usm-dark text-white font-semibold py-3 px-4 rounded-xl text-sm flex items-center justify-center gap-2 transition shadow"
          >
            <LogIn className="w-4 h-4" />
            Ingresar al Portal
          </button>
        </form>
      </div>
    </div>
  );
};
