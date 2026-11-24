import React, { useState } from 'react';
import { RolUsuario, Usuario } from '../types';
import { ArrowRight, GraduationCap, UserCheck } from 'lucide-react';
import logoUsm from '../resources/marca-color.png';

interface LoginProps {
  onLogin: (usuario: Usuario) => void;
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [nombre, setNombre] = useState('');
  const [rol, setRol] = useState<RolUsuario>('alumno');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const nombreFinal =
      nombre.trim() || (rol === 'alumno' ? 'Estudiante USM' : 'Profesor USM');
    onLogin({ nombre: nombreFinal, rol });
  };

  return (
    <div className="min-h-screen w-screen bg-white text-slate-900 grid grid-cols-1 lg:grid-cols-12">
      {/* Panel izquierdo: degradado azul suave de medio oscuro a medio claro */}
      <section className="relative lg:col-span-7 flex flex-col justify-center p-10 sm:p-14 lg:p-20 overflow-hidden bg-gradient-to-br from-[#234E86] via-[#4378B8] to-[#83B7E8] text-white">
        {/* Retícula arquitectónica muy sutil */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.1]"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(255, 255, 255, 0.35) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.35) 1px, transparent 1px)',
            backgroundSize: '56px 56px',
          }}
        />

        {/* Destello suave de luz para profundidad */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-32 -right-24 h-[28rem] w-[28rem] rounded-full bg-white/15 blur-3xl"
        />

        {/* Nombre de la IA y explicación resumida */}
        <div className="relative z-10 max-w-xl">
          <h1 className="font-display text-6xl sm:text-7xl xl:text-8xl font-extrabold tracking-tight leading-none text-white">
            LuzIA
          </h1>
          <div className="mt-5 h-[3px] w-16 bg-usm-gold" />
          <p className="mt-6 text-base sm:text-lg text-white/90 leading-relaxed max-w-md font-normal">
            Asistencia académica conectada directamente al material oficial de
            tus asignaturas. Resuelve dudas paso a paso con guía socrática y
            supervisión docente.
          </p>
        </div>
      </section>

      {/* Panel derecho: Login lateral amplio sobre blanco */}
      <main className="lg:col-span-5 flex flex-col justify-between bg-white px-8 py-12 sm:px-14 lg:px-16">
        <header className="flex items-center justify-between">
          <img
            src={logoUsm}
            alt="Universidad Técnica Federico Santa María"
            className="h-9 sm:h-10 object-contain"
          />
        </header>

        <div className="w-full max-w-md mx-auto my-auto py-10">
          <div className="mb-10">
            <h2 className="font-display text-3xl font-bold tracking-tight text-slate-950">
              Iniciar sesión
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Selecciona tu perfil e ingresa tus credenciales institucionales.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Selector de perfil tipo pestañas limpias */}
            <div>
              <label className="block font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 mb-3">
                Perfil de acceso
              </label>
              <div className="grid grid-cols-2 border-b border-slate-200">
                <button
                  type="button"
                  onClick={() => setRol('alumno')}
                  className={`relative pb-3.5 pt-2 flex items-center justify-center gap-2.5 text-sm font-semibold transition-colors ${
                    rol === 'alumno'
                      ? 'text-usm-blue'
                      : 'text-slate-400 hover:text-slate-700'
                  }`}
                >
                  <GraduationCap className="w-4 h-4" />
                  <span>Estudiante</span>
                  {rol === 'alumno' && (
                    <span className="absolute bottom-[-1px] left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#0A3A82] to-[#3B9BFF]" />
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setRol('docente')}
                  className={`relative pb-3.5 pt-2 flex items-center justify-center gap-2.5 text-sm font-semibold transition-colors ${
                    rol === 'docente'
                      ? 'text-usm-blue'
                      : 'text-slate-400 hover:text-slate-700'
                  }`}
                >
                  <UserCheck className="w-4 h-4" />
                  <span>Docente</span>
                  {rol === 'docente' && (
                    <span className="absolute bottom-[-1px] left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#0A3A82] to-[#3B9BFF]" />
                  )}
                </button>
              </div>
            </div>

            {/* Campo de entrada limpio con línea inferior */}
            <div>
              <label
                htmlFor="login-identidad"
                className="block font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 mb-2"
              >
                Nombre o correo institucional
              </label>
              <input
                id="login-identidad"
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder={
                  rol === 'alumno'
                    ? 'nombre.apellido@usm.cl'
                    : 'profesor.asignatura@usm.cl'
                }
                className="w-full bg-slate-50/70 px-3.5 py-3.5 text-sm text-slate-900 placeholder:text-slate-400 border-b-2 border-slate-200 focus:border-usm-blue focus:bg-white focus:outline-none transition-colors rounded-none"
              />
              <p className="mt-2 text-xs text-slate-400">
                Puedes dejarlo vacío para ingresar con un perfil de prueba.
              </p>
            </div>

            {/* Botón principal con degradado azul sutil de alto contraste */}
            <button
              type="submit"
              className="group w-full bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-110 active:scale-[0.995] text-white font-display font-semibold py-4 px-5 rounded-sm text-sm tracking-wide flex items-center justify-between transition-all"
            >
              <span>Ingresar al portal</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </button>
          </form>
        </div>

        <footer className="pt-6 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Ex Umbra in Solem</span>
          <span>LuzIA USM</span>
        </footer>
      </main>
    </div>
  );
};
