import React, { useEffect, useState } from 'react';
import { CalendarClock, ClipboardList, Pencil, Plus, Save, Trash2, X } from 'lucide-react';
import { TareaJeff } from '../../types';
import {
  actualizarTarea,
  crearTarea,
  eliminarTarea,
  listarTareas,
} from '../../services/api';

interface TareasJeffPanelProps {
  codigoRamo: string;
  onNotify: (tipo: 'exito' | 'error', texto: string) => void;
}

interface BorradorTarea {
  titulo: string;
  fecha_limite: string;
  formato_entrega: string;
  plataforma: string;
  palabras_clave: string;
  respuesta: string;
}

const borradorVacio: BorradorTarea = {
  titulo: '',
  fecha_limite: '',
  formato_entrega: '',
  plataforma: '',
  palabras_clave: '',
  respuesta: '',
};

export const TareasJeffPanel: React.FC<TareasJeffPanelProps> = ({
  codigoRamo,
  onNotify,
}) => {
  const [tareas, setTareas] = useState<TareaJeff[]>([]);
  const [cargando, setCargando] = useState<boolean>(false);
  const [guardando, setGuardando] = useState<boolean>(false);
  const [eliminandoId, setEliminandoId] = useState<string | null>(null);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState<boolean>(false);
  const [borrador, setBorrador] = useState<BorradorTarea>(borradorVacio);

  const cargarTareas = async () => {
    setCargando(true);
    try {
      setTareas(await listarTareas(codigoRamo));
    } catch (err) {
      onNotify(
        'error',
        err instanceof Error ? err.message : 'No se pudieron cargar las tareas.'
      );
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    cargarTareas();
    setMostrarFormulario(false);
    setEditandoId(null);
    setBorrador(borradorVacio);
  }, [codigoRamo]);

  const cambiarBorrador = (campo: keyof BorradorTarea, valor: string) => {
    setBorrador((prev) => ({ ...prev, [campo]: valor }));
  };

  const abrirNueva = () => {
    setEditandoId(null);
    setBorrador(borradorVacio);
    setMostrarFormulario(true);
  };

  const abrirEdicion = (tarea: TareaJeff) => {
    setEditandoId(tarea.id);
    setBorrador({
      titulo: tarea.titulo || '',
      fecha_limite: tarea.fecha_limite || '',
      formato_entrega: tarea.formato_entrega || '',
      plataforma: tarea.plataforma || '',
      palabras_clave: (tarea.palabras_clave || []).join(', '),
      respuesta: tarea.respuesta || '',
    });
    setMostrarFormulario(true);
  };

  const cancelar = () => {
    setMostrarFormulario(false);
    setEditandoId(null);
    setBorrador(borradorVacio);
  };

  const guardar = async (event: React.FormEvent) => {
    event.preventDefault();
    const titulo = borrador.titulo.trim();
    if (!titulo) {
      onNotify('error', 'El título de la tarea es obligatorio.');
      return;
    }

    const palabras = borrador.palabras_clave
      .split(',')
      .map((palabra) => palabra.trim())
      .filter((palabra) => palabra.length >= 3);

    const payload = {
      titulo,
      fecha_limite: borrador.fecha_limite.trim() || undefined,
      formato_entrega: borrador.formato_entrega.trim() || undefined,
      plataforma: borrador.plataforma.trim() || undefined,
      palabras_clave: palabras.length > 0 ? palabras : undefined,
      respuesta: borrador.respuesta.trim() || undefined,
    };

    setGuardando(true);
    try {
      if (editandoId) {
        const tarea = await actualizarTarea(codigoRamo, editandoId, payload);
        setTareas((prev) => prev.map((item) => (item.id === editandoId ? tarea : item)));
        onNotify('exito', 'Tarea actualizada. Jeff responderá con estos datos.');
      } else {
        const tarea = await crearTarea(codigoRamo, payload);
        setTareas((prev) => [...prev, tarea]);
        onNotify('exito', 'Tarea creada. Jeff responderá con estos datos.');
      }
      cancelar();
    } catch (err) {
      onNotify(
        'error',
        err instanceof Error ? err.message : 'No se pudo guardar la tarea.'
      );
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async (tarea: TareaJeff) => {
    if (!window.confirm(`¿Eliminar la tarea "${tarea.titulo}"?`)) return;
    setEliminandoId(tarea.id);
    try {
      await eliminarTarea(codigoRamo, tarea.id);
      setTareas((prev) => prev.filter((item) => item.id !== tarea.id));
      if (editandoId === tarea.id) cancelar();
      onNotify('exito', 'Tarea eliminada.');
    } catch (err) {
      onNotify(
        'error',
        err instanceof Error ? err.message : 'No se pudo eliminar la tarea.'
      );
    } finally {
      setEliminandoId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="pb-5 border-b border-slate-200 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h3 className="font-display text-lg font-bold text-slate-950">
            Tareas y entregas de {codigoRamo}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 max-w-2xl">
            Jeff responde estas consultas por coincidencia de palabras clave, sin consumir GPU.
          </p>
        </div>
        <button
          type="button"
          onClick={abrirNueva}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-sm bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-105 text-white font-display text-xs font-semibold transition"
        >
          <Plus className="w-4 h-4" />
          <span>Nueva tarea</span>
        </button>
      </div>

      {mostrarFormulario && (
        <form
          onSubmit={guardar}
          className="bg-white p-6 rounded-sm border border-slate-200 space-y-4"
        >
          <div className="flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-[#234E86]" />
            <h4 className="font-display text-sm font-bold text-slate-900">
              {editandoId ? 'Editar tarea' : 'Nueva tarea'}
            </h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Título
              </label>
              <input
                type="text"
                value={borrador.titulo}
                onChange={(event) => cambiarBorrador('titulo', event.target.value)}
                placeholder="Ej.: Informe Laboratorio 1"
                className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
              />
            </div>
            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Fecha límite
              </label>
              <input
                type="text"
                value={borrador.fecha_limite}
                onChange={(event) => cambiarBorrador('fecha_limite', event.target.value)}
                placeholder="Viernes 23:59 hrs"
                className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
              />
            </div>
            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Plataforma
              </label>
              <input
                type="text"
                value={borrador.plataforma}
                onChange={(event) => cambiarBorrador('plataforma', event.target.value)}
                placeholder="Buzón de Tareas en AULA USM"
                className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Formato de entrega
              </label>
              <input
                type="text"
                value={borrador.formato_entrega}
                onChange={(event) => cambiarBorrador('formato_entrega', event.target.value)}
                placeholder="PDF vía AULA USM"
                className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Palabras clave
              </label>
              <input
                type="text"
                value={borrador.palabras_clave}
                onChange={(event) => cambiarBorrador('palabras_clave', event.target.value)}
                placeholder="informe 1, entrega informe, plazo informe"
                className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Sepáralas con coma. Si las dejas vacías, se generan desde el título.
              </p>
            </div>
            <div className="md:col-span-2">
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Respuesta fija opcional
              </label>
              <textarea
                rows={3}
                value={borrador.respuesta}
                onChange={(event) => cambiarBorrador('respuesta', event.target.value)}
                placeholder="Si se completa, Jeff usará este texto en lugar de la ficha automática."
                className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={cancelar}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-sm border border-slate-300 text-xs font-semibold text-slate-600 hover:border-slate-400 transition"
            >
              <X className="w-3.5 h-3.5" />
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-sm bg-[#234E86] text-white text-xs font-semibold hover:bg-[#1B3E6E] disabled:opacity-50 transition"
            >
              <Save className="w-4 h-4" />
              {guardando ? 'Guardando...' : 'Guardar tarea'}
            </button>
          </div>
        </form>
      )}

      {cargando ? (
        <div className="bg-white p-10 rounded-sm border border-slate-200 text-center text-xs text-slate-500">
          Cargando tareas...
        </div>
      ) : tareas.length === 0 ? (
        <div className="bg-white p-12 rounded-sm border border-slate-200 text-center space-y-2">
          <ClipboardList className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="font-display text-sm font-semibold text-slate-800">
            No hay tareas configuradas
          </p>
          <p className="text-xs text-slate-500">
            Agrega una tarea para que Jeff responda fechas, formatos y plataformas de entrega.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {tareas.map((tarea) => (
            <article
              key={tarea.id}
              className="bg-white p-5 rounded-sm border border-slate-200 flex flex-wrap items-start justify-between gap-4"
            >
              <div className="space-y-2 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-display text-sm font-bold text-slate-900">
                    {tarea.titulo}
                  </h4>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded-sm bg-slate-100 text-slate-500">
                    {tarea.id}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-1 text-[11px] text-slate-500">
                  <span>
                    <strong className="text-slate-700">Fecha:</strong>{' '}
                    {tarea.fecha_limite || 'Sin fecha'}
                  </span>
                  <span>
                    <strong className="text-slate-700">Formato:</strong>{' '}
                    {tarea.formato_entrega || 'Sin formato'}
                  </span>
                  <span>
                    <strong className="text-slate-700">Plataforma:</strong>{' '}
                    {tarea.plataforma || 'Sin plataforma'}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(tarea.palabras_clave || []).map((palabra) => (
                    <span
                      key={palabra}
                      className="font-mono text-[10px] px-2 py-0.5 rounded-sm bg-blue-50 text-[#234E86] border border-blue-200"
                    >
                      {palabra}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => abrirEdicion(tarea)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-slate-200 text-xs font-semibold text-slate-600 hover:border-[#234E86] hover:text-[#234E86] transition"
                >
                  <Pencil className="w-3.5 h-3.5" />
                  Editar
                </button>
                <button
                  type="button"
                  onClick={() => eliminar(tarea)}
                  disabled={eliminandoId === tarea.id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-red-200 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  {eliminandoId === tarea.id ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};
