import React from 'react';
import { BookOpen, LogOut, GraduationCap, UserCheck, ChevronLeft, PanelLeftClose, LayoutGrid } from 'lucide-react';
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
        sidebarVisible ? 'w-72 opacity-100' : 'w-0 opacity-0 -translate-x-full overflow-hidden pointer-events-none'
      } transition-all duration-300 ease-in-out bg-usm-blue text-white flex flex-col h-full border-r border-usm-dark shadow-lg shrink-0`}
    >
      {/* Botón redondo en el borde medio de la barra para esconderla */}
      {sidebarVisible && (
        <button
          onClick={onToggleSidebar}
          title="Ocultar barra lateral"
          className="absolute top-1/2 -right-3.5 -translate-y-1/2 z-40 w-8 h-8 rounded-full bg-usm-blue text-white shadow-xl border-2 border-white hover:bg-usm-dark hover:scale-110 active:scale-95 transition-all flex items-center justify-center group"
        >
          <ChevronLeft className="w-4 h-4 text-white group-hover:-translate-x-0.5 transition-transform" />
        </button>
      )}

      {/* Encabezado AULA USM: Logo arriba, botón de esconder y Nombre de IA abajo */}
      <div className="p-4 border-b border-white/10 bg-usm-dark/40 space-y-3">
        {/* Fila del Logo Oficial + Botón claro para esconder */}
        <div className="flex items-center gap-2">
          <div className="bg-white rounded-xl p-2 flex-1 flex items-center justify-center shadow-sm">
            <img
              src={logoUsm}
              alt="Logo Institucional USM"
              className="h-9 w-auto max-w-full object-contain"
            />
          </div>

        </div>

        {/* Fila del Nombre de la IA y Rol */}
        <div className="flex items-center justify-between pt-1">
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-tight text-white">
              LuzAI <span className="text-usm-gold font-semibold text-sm">USM</span>
            </h1>
            <p className="text-xs text-blue-100/80">Tutor AULA Inteligente</p>
          </div>
          <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-usm-gold text-usm-dark uppercase tracking-wider">
            {usuario.rol}
          </span>
        </div>
      </div>

      {/* Lista de Asignaturas */}
      <div className="p-4 flex-1 overflow-y-auto">
        {/* Acceso directo a Vista General "Mis Cursos" */}
        <button
          onClick={() => onSeleccionarRamo(null)}
          className={`w-full text-left p-2.5 rounded-xl transition border text-xs font-semibold flex items-center gap-2 mb-4 ${
            ramoActivo === null
              ? 'bg-usm-dark text-white border-usm-gold shadow-sm ring-1 ring-usm-gold/40'
              : 'bg-white/5 border-white/5 hover:bg-white/10 text-blue-100 hover:text-white'
          }`}
        >
          <LayoutGrid className="w-4 h-4 text-usm-gold shrink-0" />
          <span>Panel de Inicio (Mis Cursos)</span>
        </button>

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

      {/* Zona Inferior: Perfil + Botón de Logout */}
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

        {/* Botón de Cerrar Sesión */}
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
