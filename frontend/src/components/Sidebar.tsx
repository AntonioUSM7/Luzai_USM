import React from 'react';
import { BookOpen, LogOut, User } from 'lucide-react';
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
    <aside className="w-72 bg-usm-navy text-white flex flex-col h-full border-r border-slate-800">
      {/* Header Institucional */}
      <div className="p-4 border-b border-slate-700/80 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-base tracking-tight text-white">LuzAI USM</h1>
          <p className="text-xs text-slate-300">Tutor Inteligente</p>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-usm-gold text-usm-navy uppercase">
          {usuario.rol}
        </span>
      </div>

      {/* Datos del Usuario */}
      <div className="px-4 py-3 border-b border-slate-700/60 bg-slate-900/40 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 truncate">
          <User className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="truncate text-slate-200">{usuario.nombre}</span>
        </div>
        <button
          onClick={onCerrarSesion}
          title="Cerrar Sesión"
          className="text-slate-400 hover:text-red-400 p-1 rounded transition"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>

      {/* Lista de Asignaturas */}
      <div className="p-4 flex-1 overflow-y-auto">
        <h2 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-3 flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-usm-gold" />
          Asignaturas
        </h2>

        <div className="space-y-1.5">
          {ramos.map((ramo) => {
            const activo = ramoActivo?.codigo === ramo.codigo;
            return (
              <button
                key={ramo.codigo}
                onClick={() => onSeleccionarRamo(ramo)}
                className={`w-full text-left p-2.5 rounded-xl transition border text-sm ${
                  activo
                    ? 'bg-usm-blue border-usm-gold/60 text-white font-medium shadow-sm'
                    : 'bg-slate-800/40 border-transparent hover:bg-slate-800 text-slate-300'
                }`}
              >
                <div className="font-semibold text-xs text-usm-gold">{ramo.codigo}</div>
                <div className="truncate mt-0.5">{ramo.nombre}</div>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
