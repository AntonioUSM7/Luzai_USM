import React from 'react';
import {
  BookOpen,
  LogOut,
  GraduationCap,
  UserCheck,
  ChevronLeft,
  LayoutGrid,
} from 'lucide-react';
import { Ramo, Usuario } from '../types';
import logoUsm from '../resources/marca-color.png';

interface SidebarProps {
  usuario: Usuario;
  ramos: Ramo[];
  ramoActivo: Ramo | null;
  sidebarVisible: boolean;
  onToggleSidebar: () => void;
  onSeleccionarRamo: (ramo: Ramo | null) => void;
  onCerrarSesion: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  usuario,
  ramos,
  ramoActivo,
  sidebarVisible,
  onToggleSidebar,
  onSeleccionarRamo,
  onCerrarSesion,
}) => {
  return (
    <aside
      className={`relative ${
        sidebarVisible
          ? 'w-72 opacity-100'
          : 'w-0 opacity-0 -translate-x-full overflow-hidden pointer-events-none'
      } transition-all duration-300 ease-in-out bg-gradient-to-b from-white via-[#EFF5FC] to-[#D4E5F7] text-slate-900 flex flex-col h-full border-r border-slate-200/90 shrink-0`}
    >
      {/* Botón en el borde medio para ocultar la barra */}
      {sidebarVisible && (
        <button
          onClick={onToggleSidebar}
          title="Ocultar barra lateral"
          className="absolute top-1/2 -right-3.5 -translate-y-1/2 z-40 w-7 h-7 rounded-sm bg-white text-[#1E4478] border border-slate-300 shadow-sm hover:bg-[#1E4478] hover:text-white hover:border-[#1E4478] transition-all flex items-center justify-center group"
        >
          <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
        </button>
      )}

      {/* Franja superior sólida que conecta sin corte con el degradado de la página */}
      <div
        aria-hidden="true"
        className="h-1 w-full bg-[#234E86] shrink-0"
      />

      {/* Encabezado: Logo USM integrado directamente sin cuadro blanco + LuzIA */}
      <div className="px-5 pt-5 pb-4 border-b border-slate-200/70 space-y-4">
        <div className="flex items-center">
          <img
            src={logoUsm}
            alt="Universidad Técnica Federico Santa María"
            className="h-9 w-auto max-w-full object-contain"
          />
        </div>

        <div className="flex items-end justify-between">
          <div>
            <h1 className="font-display font-extrabold text-xl leading-none tracking-tight text-slate-950">
              LuzIA <span className="text-[#3A70B2] font-bold text-sm">USM</span>
            </h1>
            <p className="text-[11px] text-slate-500 mt-1">Tutor AULA Inteligente</p>
          </div>
          <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-[#1E4478] text-white uppercase tracking-[0.12em]">
            {usuario.rol}
          </span>
        </div>
      </div>

      {/* Navegación y Lista de Asignaturas */}
      <div className="px-4 py-5 flex-1 overflow-y-auto space-y-6">
        {/* Acceso directo a Panel de Inicio (Mis Cursos) */}
        <button
          onClick={() => onSeleccionarRamo(null)}
          className={`w-full text-left px-3 py-2.5 rounded-sm transition text-xs font-semibold flex items-center gap-2.5 border-l-2 ${
            ramoActivo === null
              ? 'bg-white/90 text-[#1E4478] border-l-[#1E4478] shadow-[0_1px_2px_rgba(30,68,120,0.06)]'
              : 'border-l-transparent text-slate-600 hover:bg-white/60 hover:text-slate-950'
          }`}
        >
          <LayoutGrid
            className={`w-4 h-4 shrink-0 ${
              ramoActivo === null ? 'text-[#234E86]' : 'text-slate-400'
            }`}
          />
          <span>Panel de Inicio (Mis Cursos)</span>
        </button>

        <div>
          <h2 className="px-2 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500 font-semibold mb-2.5 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-[#3A70B2]" />
            <span>Mis Asignaturas</span>
          </h2>

          <div className="space-y-1.5">
            {ramos.map((ramo) => {
              const activo = ramoActivo?.codigo === ramo.codigo;
              return (
                <button
                  key={ramo.codigo}
                  onClick={() => onSeleccionarRamo(ramo)}
                  className={`w-full text-left px-3 py-3 rounded-sm transition border-l-2 ${
                    activo
                      ? 'bg-[#1E4478]/[0.14] border-l-[#1E4478] text-slate-950'
                      : 'bg-[#1E4478]/[0.06] border-l-transparent hover:bg-[#1E4478]/[0.11] text-slate-700 hover:text-slate-950'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`font-mono text-[11px] font-bold tracking-wider ${
                        activo ? 'text-[#1E4478]' : 'text-[#3A70B2]'
                      }`}
                    >
                      {ramo.codigo}
                    </span>
                    {activo && (
                      <span className="font-mono text-[9px] uppercase tracking-wider text-[#1E4478] bg-[#E6F0FA] px-1.5 py-0.5 rounded-sm font-semibold">
                        Activo
                      </span>
                    )}
                  </div>
                  <div
                    className={`mt-1 leading-snug line-clamp-2 text-xs ${
                      activo ? 'font-display font-bold text-slate-950' : 'font-medium text-slate-600'
                    }`}
                  >
                    {ramo.nombre}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Zona Inferior: Perfil + Cerrar Sesión */}
      <div className="p-4 border-t border-[#1E4478]/10 bg-white/40 backdrop-blur-[2px] space-y-3">
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-8 h-8 rounded-sm bg-[#1E4478] text-white flex items-center justify-center shrink-0">
            {usuario.rol === 'alumno' ? (
              <GraduationCap className="w-4 h-4" />
            ) : (
              <UserCheck className="w-4 h-4" />
            )}
          </div>
          <div className="truncate">
            <p className="font-display text-xs font-bold text-slate-900 truncate">
              {usuario.nombre}
            </p>
            <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
              {usuario.rol}
            </p>
          </div>
        </div>

        <button
          onClick={onCerrarSesion}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-sm border border-red-300/80 bg-white/80 hover:bg-red-600 hover:border-red-600 text-red-600 hover:text-white font-display font-semibold text-xs transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
};
