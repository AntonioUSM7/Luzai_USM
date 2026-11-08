import React from 'react';
import { BookOpen, LogOut, User, GraduationCap, UserCheck } from 'lucide-react';
import { Ramo, Usuario } from '../types';

interface SidebarProps {
  usuario: Usuario;
  ramos: Ramo[];
  ramoActivo: Ramo | null;
  onSeleccionarRamo: (ramo: Ramo) => void;
  onCerrarSesion: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  usuario,
  ramos,
  ramoActivo,
  onSeleccionarRamo,
  onCerrarSesion,
}) => {
  return (
    <aside className="w-72 bg-usm-blue text-white flex flex-col h-full border-r border-usm-dark shadow-lg">
      {/* Encabezado AULA USM */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between bg-usm-dark/40">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-white text-usm-blue font-black text-lg flex items-center justify-center shadow-sm">
            USM
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight tracking-tight text-white">
              LuzAI <span className="text-usm-gold text-xs font-semibold">USM</span>
            </h1>
            <p className="text-[11px] text-blue-100/80">Tutor AULA Inteligente</p>
          </div>
        </div>

        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-usm-gold text-usm-dark uppercase tracking-wider">
          {usuario.rol}
        </span>
      </div>

      {/* Lista de Asignaturas */}
      <div className="p-4 flex-1 overflow-y-auto">
        <h2 className="text-[11px] uppercase tracking-wider text-blue-200/90 font-bold mb-3 flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-usm-gold" />
          Mis Asignaturas
        </h2>

        <div className="space-y-2">
          {ramos.map((ramo) => {
            const activo = ramoActivo?.codigo === ramo.codigo;
            return (
              <button
                key={ramo.codigo}
                onClick={() => onSeleccionarRamo(ramo)}
                className={`w-full text-left p-3 rounded-xl transition border text-sm ${
                  activo
                    ? 'bg-usm-dark text-white font-semibold border-usm-gold/80 shadow-md ring-1 ring-usm-gold/40'
                    : 'bg-white/5 border-white/5 hover:bg-white/10 text-blue-100 hover:text-white'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-usm-gold">{ramo.codigo}</span>
                  {activo && (
                    <span className="text-[10px] bg-usm-gold/20 text-usm-gold px-1.5 py-0.2 rounded font-medium">
                      Activo
                    </span>
                  )}
                </div>
                <div className="mt-1 leading-snug line-clamp-2 text-xs">{ramo.nombre}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Zona Inferior: Perfil + Botón de Logout Notorio */}
      <div className="p-4 border-t border-white/10 bg-usm-dark/60 space-y-3">
        {/* Identificación del Usuario */}
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-white/5 border border-white/5">
          <div className="w-8 h-8 rounded-full bg-blue-100 text-usm-blue flex items-center justify-center shrink-0">
            {usuario.rol === 'alumno' ? (
              <GraduationCap className="w-4 h-4" />
            ) : (
              <UserCheck className="w-4 h-4" />
            )}
          </div>
          <div className="truncate">
            <p className="text-xs font-semibold text-white truncate">{usuario.nombre}</p>
            <p className="text-[10px] text-blue-200/70 capitalize">{usuario.rol}</p>
          </div>
        </div>

        {/* Botón de Cerrar Sesión Notorio y Visible */}
        <button
          onClick={onCerrarSesion}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-red-600/90 hover:bg-red-600 text-white font-semibold text-xs transition shadow-md hover:shadow-lg active:scale-[0.99] border border-red-400/40"
        >
          <LogOut className="w-4 h-4" />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
};
