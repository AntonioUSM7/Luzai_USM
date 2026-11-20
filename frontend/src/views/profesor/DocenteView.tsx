import React, { useState, useEffect, useRef } from 'react';
import { Ramo, ArchivoRecurso, ConsultaProfesor } from '../../types';
import {
  ArrowLeft,
  BookOpen,
  Folder,
  FolderOpen,
  FolderPlus,
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  Clock,
  Sparkles,
  Bot,
  BarChart3,
  X,
  Plus,
  CornerDownRight,
  MessageSquareMore,
  Send,
} from 'lucide-react';
import {
  listarArchivosRamo,
  subirArchivoRamo,
  eliminarArchivoRamo,
  crearCarpetaRamo,
  eliminarCarpetaRamo,
  listarConsultasProfesor,
  responderConsultaProfesor,
} from '../../services/api';

interface DocenteViewProps {
  ramos: Ramo[];
  ramoActivo: Ramo | null;
  onSeleccionarRamo: (ramo: Ramo | null) => void;
}

export const DocenteView: React.FC<DocenteViewProps> = ({
  ramos,
  ramoActivo,
  onSeleccionarRamo,
}) => {
  // Pestaña activa dentro del ramo
  const [subTab, setSubTab] = useState<'archivos' | 'consultas' | 'jeff' | 'socratico' | 'analitica'>('archivos');

  // Estado del buzón de consultas escaladas por alumnos
  const [consultas, setConsultas] = useState<ConsultaProfesor[]>([]);
  const [cargandoConsultas, setCargandoConsultas] = useState<boolean>(false);
  const [filtroConsultas, setFiltroConsultas] = useState<'pendiente' | 'resuelta' | 'descartada' | 'todas'>('pendiente');
  const [borradoresRespuesta, setBorradoresRespuesta] = useState<
    Record<string, { texto: string; guardarEnJeff: boolean; palabrasClave: string; categoria: string }>
  >({});
  const [procesandoConsultaId, setProcesandoConsultaId] = useState<string | null>(null);

  // Estado del gestor de archivos
  const [carpetas, setCarpetas] = useState<string[]>([]);
  const [carpetaSeleccionada, setCarpetaSeleccionada] = useState<string | null>(null); // null = raíz
  const [archivos, setArchivos] = useState<ArchivoRecurso[]>([]);
  const [cargando, setCargando] = useState<boolean>(false);

  // Estado de creación de carpeta
  const [mostrarCrearCarpeta, setMostrarCrearCarpeta] = useState<boolean>(false);
  const [nombreNuevaCarpeta, setNombreNuevaCarpeta] = useState<string>('');
  const [creandoCarpeta, setCreandoCarpeta] = useState<boolean>(false);

  // Estado de la ventana modal superpuesta para subir archivos
  const [modalSubirAbierto, setModalSubirAbierto] = useState<boolean>(false);
  const [archivoParaSubir, setArchivoParaSubir] = useState<File | null>(null);
  const [carpetaDestinoSubida, setCarpetaDestinoSubida] = useState<string>('Clases');
  const [subiendoArchivo, setSubiendoArchivo] = useState<boolean>(false);

  // Alertas
  const [notificacion, setNotificacion] = useState<{ tipo: 'exito' | 'error'; texto: string } | null>(null);

  const fileInputModalRef = useRef<HTMLInputElement>(null);

  const mostrarMensaje = (tipo: 'exito' | 'error', texto: string) => {
    setNotificacion({ tipo, texto });
    setTimeout(() => setNotificacion(null), 4000);
  };

  // Helper de categoría para las tarjetas del inicio
  const obtenerCategoria = (ramo: Ramo) => {
    if (ramo.codigo.startsWith('MAT')) return 'MATEMÁTICA';
    if (ramo.codigo.startsWith('TEL')) return 'ELECTRÓNICA';
    if (ramo.codigo.startsWith('INF')) return 'INFORMÁTICA';
    return 'INGENIERÍA';
  };

  // Cargar carpetas y archivos cuando se selecciona un ramo
  const cargarDatosRamo = async () => {
    if (!ramoActivo) return;
    setCargando(true);
    try {
      const resp = await listarArchivosRamo(ramoActivo.codigo);
      setCarpetas(resp.carpetas);
      setArchivos(resp.archivos);
      if (resp.carpetas.length > 0 && !carpetaDestinoSubida) {
        setCarpetaDestinoSubida(resp.carpetas[0]);
      }
    } catch (err) {
      console.error(err);
      mostrarMensaje('error', 'Error al cargar los archivos del ramo.');
    } finally {
      setCargando(false);
    }
  };

  const cargarConsultasRamo = async () => {
    if (!ramoActivo) return;
    setCargandoConsultas(true);
    try {
      const lista = await listarConsultasProfesor(ramoActivo.codigo);
      setConsultas(lista);
      setBorradoresRespuesta((prev) => {
        const siguiente = { ...prev };
        for (const item of lista) {
          if (!siguiente[item.id]) {
            siguiente[item.id] = {
              texto: item.respuesta_profesor || '',
              guardarEnJeff: true,
              palabrasClave: (item.palabras_clave_sugeridas || []).join(', '),
              categoria: 'Consultas Resueltas',
            };
          }
        }
        return siguiente;
      });
    } catch (err) {
      console.error(err);
      mostrarMensaje('error', 'Error al cargar las consultas de los alumnos.');
    } finally {
      setCargandoConsultas(false);
    }
  };

  useEffect(() => {
    cargarDatosRamo();
    cargarConsultasRamo();
    setCarpetaSeleccionada(null);
  }, [ramoActivo?.codigo]);

  const actualizarBorrador = (
    consultaId: string,
    cambios: Partial<{ texto: string; guardarEnJeff: boolean; palabrasClave: string; categoria: string }>
  ) => {
    setBorradoresRespuesta((prev) => ({
      ...prev,
      [consultaId]: {
        texto: prev[consultaId]?.texto ?? '',
        guardarEnJeff: prev[consultaId]?.guardarEnJeff ?? true,
        palabrasClave: prev[consultaId]?.palabrasClave ?? '',
        categoria: prev[consultaId]?.categoria ?? 'Consultas Resueltas',
        ...cambios,
      },
    }));
  };

  const manejarResponderConsulta = async (
    consulta: ConsultaProfesor,
    estado: 'resuelta' | 'descartada'
  ) => {
    if (!ramoActivo) return;
    const borrador = borradoresRespuesta[consulta.id] || {
      texto: '',
      guardarEnJeff: false,
      palabrasClave: (consulta.palabras_clave_sugeridas || []).join(', '),
      categoria: 'Consultas Resueltas',
    };

    const guardarEnJeff = estado === 'resuelta' && borrador.guardarEnJeff && borrador.texto.trim().length > 0;
    const claves = borrador.palabrasClave
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length >= 3);

    if (guardarEnJeff && claves.length === 0) {
      mostrarMensaje('error', 'Agrega al menos una palabra clave (3+ caracteres) para guardar en Jeff.');
      return;
    }

    setProcesandoConsultaId(consulta.id);
    try {
      const resp = await responderConsultaProfesor(ramoActivo.codigo, consulta.id, {
        estado,
        respuesta_profesor: estado === 'resuelta' ? borrador.texto.trim() || undefined : undefined,
        guardar_en_jeff: guardarEnJeff,
        categoria: borrador.categoria.trim() || 'Consultas Resueltas',
        palabras_clave: guardarEnJeff ? claves : undefined,
      });
      setConsultas((prev) => prev.map((c) => (c.id === consulta.id ? resp.consulta : c)));
      if (estado === 'descartada') {
        mostrarMensaje('exito', 'Consulta descartada.');
      } else if (guardarEnJeff) {
        mostrarMensaje('exito', 'Respuesta guardada y agregada a las FAQs de Jeff ($0 GPU).');
      } else {
        mostrarMensaje('exito', 'Consulta marcada como resuelta.');
      }
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'No se pudo actualizar la consulta.'
      );
    } finally {
      setProcesandoConsultaId(null);
    }
  };

  // Crear nueva carpeta
  const manejarCrearCarpeta = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo || !nombreNuevaCarpeta.trim()) return;

    setCreandoCarpeta(true);
    try {
      const nombreCreado = await crearCarpetaRamo(ramoActivo.codigo, nombreNuevaCarpeta.trim());
      setCarpetas((prev) => (prev.includes(nombreCreado) ? prev : [...prev, nombreCreado]));
      setCarpetaDestinoSubida(nombreCreado);
      setCarpetaSeleccionada(nombreCreado);
      setNombreNuevaCarpeta('');
      setMostrarCrearCarpeta(false);
      mostrarMensaje('exito', `Carpeta "${nombreCreado}" creada con éxito.`);
    } catch {
      mostrarMensaje('error', 'No se pudo crear la carpeta.');
    } finally {
      setCreandoCarpeta(false);
    }
  };

  // Subir archivo desde la ventana modal
  const manejarSubidaModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo || !archivoParaSubir) return;

    setSubiendoArchivo(true);
    try {
      const nuevo = await subirArchivoRamo(ramoActivo.codigo, archivoParaSubir, carpetaDestinoSubida);
      setArchivos((prev) => [nuevo, ...prev.filter((a) => a.nombre !== nuevo.nombre)]);
      setModalSubirAbierto(false);
      setArchivoParaSubir(null);
      mostrarMensaje('exito', `Archivo "${nuevo.nombre}" subido a la carpeta "${carpetaDestinoSubida}".`);
    } catch {
      mostrarMensaje('error', 'Ocurrió un error al subir el archivo.');
    } finally {
      setSubiendoArchivo(false);
    }
  };

  // Eliminar archivo
  const manejarEliminarArchivo = async (archivo: ArchivoRecurso) => {
    if (!ramoActivo) return;
    const seguro = window.confirm(`¿Estás seguro de eliminar el archivo "${archivo.nombre}" de la carpeta "${archivo.carpeta}"?`);
    if (!seguro) return;

    try {
      await eliminarArchivoRamo(ramoActivo.codigo, archivo.carpeta, archivo.nombre);
      setArchivos((prev) => prev.filter((a) => !(a.nombre === archivo.nombre && a.carpeta === archivo.carpeta)));
      mostrarMensaje('exito', `Archivo "${archivo.nombre}" eliminado correctamente.`);
    } catch {
      mostrarMensaje('error', 'No se pudo eliminar el archivo.');
    }
  };

  // Eliminar carpeta completa
  const manejarEliminarCarpeta = async (e: React.MouseEvent, nombreCarpeta: string) => {
    e.stopPropagation();
    if (!ramoActivo) return;

    const cantArchivos = archivos.filter((a) => a.carpeta === nombreCarpeta).length;
    const mensaje =
      cantArchivos > 0
        ? `¿Estás seguro de eliminar la carpeta "${nombreCarpeta}" y sus ${cantArchivos} archivo(s)? Esta acción eliminará permanentemente los archivos del servidor.`
        : `¿Estás seguro de eliminar la carpeta vacía "${nombreCarpeta}"?`;

    const seguro = window.confirm(mensaje);
    if (!seguro) return;

    try {
      await eliminarCarpetaRamo(ramoActivo.codigo, nombreCarpeta);
      setCarpetas((prev) => prev.filter((c) => c !== nombreCarpeta));
      setArchivos((prev) => prev.filter((a) => a.carpeta !== nombreCarpeta));
      if (carpetaSeleccionada === nombreCarpeta) {
        setCarpetaSeleccionada(null);
      }
      mostrarMensaje('exito', `Carpeta "${nombreCarpeta}" eliminada correctamente.`);
    } catch {
      mostrarMensaje('error', 'No se pudo eliminar la carpeta.');
    }
  };

  // Filtrado de archivos según carpeta seleccionada en el árbol
  const archivosMostrados = archivos.filter((a) =>
    carpetaSeleccionada === null ? true : a.carpeta === carpetaSeleccionada
  );

  // -------------------------------------------------------------
  // VISTA 1: PÁGINA DE INICIO "MIS CURSOS" (GRID ESTILO AULA USM)
  // -------------------------------------------------------------
  if (!ramoActivo) {
    return (
      <main className="flex-1 p-8 bg-[#F4F6F9] overflow-y-auto">
        <div className="max-w-6xl mx-auto space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Mis cursos</h1>
            <p className="text-xs text-slate-500 mt-1">
              Selecciona una asignatura para acceder a su configuración de recursos, tutor socrático y enrutador.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {ramos.map((ramo, index) => {
              const categoria = obtenerCategoria(ramo);
              const esPar = index % 2 === 0;

              return (
                <div
                  key={ramo.codigo}
                  onClick={() => onSeleccionarRamo(ramo)}
                  className="group bg-white rounded-xl overflow-hidden border border-slate-200 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-200 cursor-pointer flex flex-col"
                >
                  <div
                    className={`h-36 relative p-4 flex flex-col justify-between overflow-hidden ${
                      esPar
                        ? 'bg-gradient-to-br from-[#024075] via-[#05579e] to-[#0a72cc]'
                        : 'bg-gradient-to-br from-[#00274c] via-[#0b3866] to-[#164e87]'
                    }`}
                  >
                    <div className="absolute inset-0 opacity-15 pointer-events-none">
                      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                          <pattern id={`pattern-${ramo.codigo}`} width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 40 M 0 0 L 40 40" fill="none" stroke="white" strokeWidth="1" />
                            <circle cx="20" cy="20" r="3" fill="white" />
                          </pattern>
                        </defs>
                        <rect width="100%" height="100%" fill={`url(#pattern-${ramo.codigo})`} />
                      </svg>
                    </div>

                    <div className="relative z-10">
                      <span className="text-[10px] font-bold tracking-wider px-2.5 py-1 rounded-md bg-slate-900/80 text-white uppercase backdrop-blur-sm shadow-sm">
                        {categoria}
                      </span>
                    </div>

                    <div className="relative z-10 flex items-center justify-between">
                      <span className="text-xs font-bold text-usm-gold bg-black/40 px-2 py-0.5 rounded backdrop-blur-sm">
                        {ramo.codigo}
                      </span>
                      <span className="text-[11px] text-white/80 flex items-center gap-1 group-hover:text-white transition">
                        Gestionar <span className="group-hover:translate-x-0.5 transition-transform">→</span>
                      </span>
                    </div>
                  </div>

                  <div className="p-4 flex-1 flex flex-col justify-between space-y-4">
                    <div>
                      <h2 className="text-xs font-bold text-slate-800 leading-snug line-clamp-2 uppercase group-hover:text-usm-blue transition-colors">
                        (202602)({ramo.codigo}) {ramo.nombre}|Paralelos:200
                      </h2>
                      <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                        {ramo.descripcion}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-100">
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-1">
                        <div className="bg-emerald-500 h-full w-[25%] rounded-full" />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>Estado: Operativo</span>
                        <span>{ramo.documentos.length} recursos RAG</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>
    );
  }

  // -------------------------------------------------------------
  // VISTA 2: ESPACIO DE TRABAJO DEL RAMO SELECCIONADO
  // -------------------------------------------------------------
  return (
    <main className="flex-1 flex flex-col h-full bg-[#F4F6F9] overflow-hidden relative">
      {/* Cabecera del Ramo */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shadow-sm shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => onSeleccionarRamo(null)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition"
          >
            <ArrowLeft className="w-4 h-4 text-usm-blue" />
            <span>Volver a Mis cursos</span>
          </button>

          <div className="h-5 w-px bg-slate-200" />

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-usm-blue text-white">
              {ramoActivo.codigo}
            </span>
            <h1 className="text-base font-bold text-slate-800">{ramoActivo.nombre}</h1>
          </div>
        </div>

        <span className="text-xs text-slate-500 hidden sm:inline">
          {ramoActivo.departamento}
        </span>
      </header>

      {/* Sub-Pestañas del Ramo */}
      <div className="bg-white border-b border-slate-200 px-8 flex gap-6 shrink-0 shadow-sm">
        <button
          onClick={() => setSubTab('archivos')}
          className={`py-3 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            subTab === 'archivos'
              ? 'border-usm-blue text-usm-blue'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Folder className="w-4 h-4" />
          <span>Archivos del curso</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600 font-normal">
            {archivos.length}
          </span>
        </button>

        <button
          onClick={() => setSubTab('consultas')}
          className={`py-3 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            subTab === 'consultas'
              ? 'border-usm-blue text-usm-blue'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <MessageSquareMore className="w-4 h-4" />
          <span>Consultas de Alumnos</span>
          {consultas.filter((c) => c.estado === 'pendiente').length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 font-bold">
              {consultas.filter((c) => c.estado === 'pendiente').length}
            </span>
          )}
        </button>

        <button
          onClick={() => setSubTab('jeff')}
          className={`py-3 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            subTab === 'jeff'
              ? 'border-usm-blue text-usm-blue'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Bot className="w-4 h-4" />
          <span>Configuración de Jeff</span>
        </button>

        <button
          onClick={() => setSubTab('socratico')}
          className={`py-3 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            subTab === 'socratico'
              ? 'border-usm-blue text-usm-blue'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Reglas Socráticas</span>
        </button>

        <button
          onClick={() => setSubTab('analitica')}
          className={`py-3 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            subTab === 'analitica'
              ? 'border-usm-blue text-usm-blue'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Analítica Anónima</span>
        </button>
      </div>

      {/* Notificación flotante */}
      {notificacion && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl text-xs font-semibold flex items-center gap-2 border transition-all ${
            notificacion.tipo === 'exito'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-red-50 text-red-800 border-red-200'
          }`}
        >
          {notificacion.tipo === 'exito' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : (
            <X className="w-4 h-4 text-red-600" />
          )}
          <span>{notificacion.texto}</span>
        </div>
      )}

      {/* Contenido Principal */}
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* ======================================================== */}
          {/* SUB-PESTAÑA 1: EXPLORADOR DE CARPETAS Y ARCHIVOS DEL CURSO */}
          {/* ======================================================== */}
          {subTab === 'archivos' && (
            <div className="space-y-4">
              {/* Barra Superior con botón para Subir Archivos */}
              <div className="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                <div>
                  <h2 className="text-sm font-bold text-slate-800">
                    Estructura y Archivos de {ramoActivo.codigo}
                  </h2>
                  <p className="text-xs text-slate-500">
                    Navega por las carpetas del ramo o crea nuevas divisiones temáticas.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setMostrarCrearCarpeta((prev) => !prev)}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition"
                  >
                    <FolderPlus className="w-4 h-4 text-usm-blue" />
                    <span>Nueva Carpeta</span>
                  </button>

                  <button
                    onClick={() => setModalSubirAbierto(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-usm-blue hover:bg-usm-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition active:scale-[0.99]"
                  >
                    <UploadCloud className="w-4 h-4 text-usm-gold" />
                    <span>Subir Archivo</span>
                  </button>
                </div>
              </div>

              {/* Formulario rápido para crear nueva carpeta */}
              {mostrarCrearCarpeta && (
                <form
                  onSubmit={manejarCrearCarpeta}
                  className="bg-blue-50/60 p-4 rounded-2xl border border-blue-200/80 flex items-center gap-3 animate-fadeIn"
                >
                  <FolderPlus className="w-5 h-5 text-usm-blue shrink-0" />
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="Nombre de la nueva carpeta (ej. Laboratorios, Seminarios, etc.)"
                      value={nombreNuevaCarpeta}
                      onChange={(e) => setNombreNuevaCarpeta(e.target.value)}
                      className="w-full text-xs bg-white border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-usm-blue"
                      autoFocus
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={creandoCarpeta || !nombreNuevaCarpeta.trim()}
                    className="px-4 py-2 rounded-xl bg-usm-blue text-white text-xs font-bold hover:bg-usm-dark disabled:opacity-50 transition"
                  >
                    {creandoCarpeta ? 'Creando...' : 'Crear Carpeta'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setMostrarCrearCarpeta(false)}
                    className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-white/50"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </form>
              )}

              {/* Layout Dividido: Árbol de Carpetas (Izquierda) + Archivos (Derecha) */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
                {/* ------------------------------------------------ */}
                {/* ÁRBOL DE CARPETAS CON RAMAS TRADICIONALES */}
                {/* ------------------------------------------------ */}
                <div className="md:col-span-4 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100 font-sans">
                    <span className="text-[11px] uppercase tracking-wider text-slate-500 font-bold">
                      Árbol de Directorios
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                      {carpetas.length} carpetas
                    </span>
                  </div>

                  {/* Nodo Raíz: Carpeta_{CODIGO} */}
                  <div
                    onClick={() => setCarpetaSeleccionada(null)}
                    className={`flex items-center gap-2 p-2 rounded-xl cursor-pointer transition ${
                      carpetaSeleccionada === null
                        ? 'bg-usm-blue text-white font-bold shadow-sm'
                        : 'text-slate-800 hover:bg-slate-50'
                    }`}
                  >
                    <Folder className={`w-4 h-4 ${carpetaSeleccionada === null ? 'text-usm-gold' : 'text-usm-blue'}`} />
                    <span className="truncate">Carpeta_{ramoActivo.codigo}</span>
                    <span className={`ml-auto text-[10px] px-1.5 py-0.2 rounded-full ${carpetaSeleccionada === null ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'}`}>
                      {archivos.length}
                    </span>
                  </div>

                  {/* Ramas Tradicionales */}
                  <div className="pl-3 border-l-2 border-slate-200 ml-3 space-y-1">
                    {carpetas.map((cat, idx) => {
                      const esUltimo = idx === carpetas.length - 1;
                      const activa = carpetaSeleccionada === cat;
                      const cantArchivos = archivos.filter((a) => a.carpeta === cat).length;

                      return (
                        <div key={cat} className="relative flex items-center">
                          {/* Línea horizontal de rama |-- */}
                          <div className="w-3 border-t-2 border-slate-200 mr-1.5 shrink-0" />

                          <div
                            onClick={() => setCarpetaSeleccionada(cat)}
                            className={`flex-1 flex items-center justify-between p-2 rounded-xl transition cursor-pointer group ${
                              activa
                                ? 'bg-usm-dark text-white font-bold shadow-sm'
                                : 'text-slate-700 hover:bg-slate-50'
                            }`}
                          >
                            <div className="flex items-center gap-1.5 min-w-0">
                              {activa ? (
                                <FolderOpen className="w-4 h-4 text-usm-gold shrink-0" />
                              ) : (
                                <Folder className="w-4 h-4 text-slate-400 shrink-0" />
                              )}
                              <span className="truncate">{cat}</span>
                            </div>

                            <div className="flex items-center gap-1 shrink-0">
                              <span
                                className={`text-[10px] px-1.5 py-0.2 rounded-full font-sans ${
                                  activa ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-400'
                                }`}
                              >
                                {cantArchivos}
                              </span>

                              <button
                                onClick={(e) => manejarEliminarCarpeta(e, cat)}
                                title={`Eliminar carpeta "${cat}"`}
                                className={`p-1 rounded-md opacity-0 group-hover:opacity-100 transition ${
                                  activa
                                    ? 'text-white/60 hover:text-red-300 hover:bg-white/10'
                                    : 'text-slate-400 hover:text-red-600 hover:bg-red-50'
                                }`}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* ------------------------------------------------ */}
                {/* EXPLORADOR DE ARCHIVOS DE LA CARPETA SELECCIONADA */}
                {/* ------------------------------------------------ */}
                <div className="md:col-span-8 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  {/* Encabezado del explorador */}
                  <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400">Ruta:</span>
                      <span className="font-mono text-slate-600 font-semibold">
                        Carpeta_{ramoActivo.codigo} /
                      </span>
                      <span className="font-mono text-usm-blue font-bold">
                        {carpetaSeleccionada || 'Todas las carpetas'}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-400">
                        {archivosMostrados.length} archivo(s)
                      </span>

                      {carpetaSeleccionada && (
                        <button
                          onClick={(e) => manejarEliminarCarpeta(e, carpetaSeleccionada)}
                          title={`Eliminar carpeta "${carpetaSeleccionada}"`}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold text-red-600 hover:bg-red-50 border border-red-200 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Eliminar Carpeta</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {cargando ? (
                    <div className="p-12 text-center text-xs text-slate-400">
                      Cargando archivos del repositorio...
                    </div>
                  ) : archivosMostrados.length === 0 ? (
                    <div className="p-12 text-center space-y-3">
                      <FolderOpen className="w-10 h-10 text-slate-300 mx-auto" />
                      <p className="text-sm font-semibold text-slate-700">
                        {carpetaSeleccionada
                          ? `No hay archivos en la carpeta "${carpetaSeleccionada}"`
                          : 'No hay archivos en este curso aún'}
                      </p>
                      <p className="text-xs text-slate-400 max-w-sm mx-auto">
                        Presiona el botón "Subir Archivo" para cargar PDFs y asignarlos a esta u otra carpeta.
                      </p>
                      <button
                        onClick={() => {
                          if (carpetaSeleccionada) setCarpetaDestinoSubida(carpetaSeleccionada);
                          setModalSubirAbierto(true);
                        }}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-usm-blue text-white text-xs font-semibold hover:bg-usm-dark transition shadow-sm"
                      >
                        <UploadCloud className="w-4 h-4 text-usm-gold" />
                        <span>Subir archivo aquí</span>
                      </button>
                    </div>
                  ) : (
                    <ul className="divide-y divide-slate-100">
                      {archivosMostrados.map((archivo) => (
                        <li
                          key={archivo.nombre}
                          className="p-4 flex items-center justify-between hover:bg-slate-50/70 transition"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center shrink-0 border border-red-100">
                              <FileText className="w-5 h-5" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-slate-800 truncate">
                                {archivo.nombre}
                              </p>
                              <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                                <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                                  📁 {archivo.carpeta}
                                </span>
                                <span>·</span>
                                <span>{archivo.tamano_legible}</span>
                                <span>·</span>
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {archivo.fecha_modificacion}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 shrink-0">
                            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              Indexado en RAG
                            </span>

                            <button
                              onClick={() => manejarEliminarArchivo(archivo)}
                              title="Eliminar archivo"
                              className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* BUZÓN DE CONSULTAS ESCALADAS AL PROFESOR */}
          {subTab === 'consultas' && (
            <div className="space-y-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-800">
                    Buzón de Consultas Escaladas ({ramoActivo.codigo})
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Preguntas que ni Jeff ni el tutor socrático pudieron responder con respaldo y que los estudiantes enviaron para tu revisión.
                  </p>
                </div>
                <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
                  {(['pendiente', 'resuelta', 'descartada', 'todas'] as const).map((estado) => (
                    <button
                      key={estado}
                      type="button"
                      onClick={() => setFiltroConsultas(estado)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition ${
                        filtroConsultas === estado
                          ? 'bg-white text-usm-blue shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {estado === 'todas' ? 'Todas' : `${estado}s`}
                    </button>
                  ))}
                </div>
              </div>

              {cargandoConsultas ? (
                <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-xs text-slate-500">
                  Cargando consultas...
                </div>
              ) : (
                (() => {
                  const visibles =
                    filtroConsultas === 'todas'
                      ? consultas
                      : consultas.filter((c) => c.estado === filtroConsultas);

                  if (visibles.length === 0) {
                    return (
                      <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-1.5">
                        <MessageSquareMore className="w-8 h-8 text-slate-300 mx-auto" />
                        <p className="text-sm font-semibold text-slate-700">
                          No hay consultas en esta categoría
                        </p>
                        <p className="text-xs text-slate-500">
                          Cuando un alumno escale una duda desde el chat, aparecerá aquí.
                        </p>
                      </div>
                    );
                  }

                  return (
                    <div className="space-y-3">
                      {visibles.map((consulta) => {
                        const borrador = borradoresRespuesta[consulta.id] || {
                          texto: consulta.respuesta_profesor || '',
                          guardarEnJeff: true,
                          palabrasClave: (consulta.palabras_clave_sugeridas || []).join(', '),
                          categoria: 'Consultas Resueltas',
                        };
                        const ocupada = procesandoConsultaId === consulta.id;

                        return (
                          <div
                            key={consulta.id}
                            className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <div className="space-y-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span
                                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                                      consulta.estado === 'pendiente'
                                        ? 'bg-amber-100 text-amber-800'
                                        : consulta.estado === 'resuelta'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : 'bg-slate-200 text-slate-600'
                                    }`}
                                  >
                                    {consulta.estado}
                                  </span>
                                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                    {consulta.motivo === 'fuera_de_foco'
                                      ? 'Fuera de foco'
                                      : 'Sin respaldo RAG'}
                                  </span>
                                  {consulta.guardada_en_jeff && (
                                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-usm-blue border border-blue-200">
                                      Guardada en Jeff ($0 GPU)
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm font-semibold text-slate-800">
                                  “{consulta.pregunta}”
                                </p>
                              </div>
                              <span className="text-[11px] text-slate-400">
                                {consulta.fecha_creacion.replace('T', ' ')}
                              </span>
                            </div>

                            {consulta.estado === 'pendiente' ? (
                              <div className="space-y-3 pt-2 border-t border-slate-100">
                                <div>
                                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                                    Respuesta del docente
                                  </label>
                                  <textarea
                                    rows={3}
                                    value={borrador.texto}
                                    onChange={(e) =>
                                      actualizarBorrador(consulta.id, { texto: e.target.value })
                                    }
                                    placeholder="Escribe una respuesta clara (si activas Jeff, esta respuesta se entregará automáticamente a futuros alumnos)..."
                                    className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-usm-blue"
                                  />
                                </div>

                                <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={borrador.guardarEnJeff}
                                    onChange={(e) =>
                                      actualizarBorrador(consulta.id, {
                                        guardarEnJeff: e.target.checked,
                                      })
                                    }
                                    className="rounded border-slate-300 text-usm-blue focus:ring-usm-blue"
                                  />
                                  <span className="font-medium">
                                    Guardar como FAQ de Jeff para responder futuras dudas iguales a $0 GPU
                                  </span>
                                </label>

                                {borrador.guardarEnJeff && (
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                                    <div>
                                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                                        Palabras clave (separadas por coma)
                                      </label>
                                      <input
                                        type="text"
                                        value={borrador.palabrasClave}
                                        onChange={(e) =>
                                          actualizarBorrador(consulta.id, {
                                            palabrasClave: e.target.value,
                                          })
                                        }
                                        placeholder="ej: efecto tunel, cuantico, schrodinger"
                                        className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-usm-blue"
                                      />
                                    </div>
                                    <div>
                                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                                        Categoría en Jeff
                                      </label>
                                      <input
                                        type="text"
                                        value={borrador.categoria}
                                        onChange={(e) =>
                                          actualizarBorrador(consulta.id, {
                                            categoria: e.target.value,
                                          })
                                        }
                                        className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-usm-blue"
                                      />
                                    </div>
                                  </div>
                                )}

                                <div className="flex flex-wrap items-center justify-end gap-2">
                                  <button
                                    type="button"
                                    disabled={ocupada}
                                    onClick={() => manejarResponderConsulta(consulta, 'descartada')}
                                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200 transition disabled:opacity-50"
                                  >
                                    Descartar
                                  </button>
                                  <button
                                    type="button"
                                    disabled={ocupada}
                                    onClick={() => manejarResponderConsulta(consulta, 'resuelta')}
                                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-usm-blue hover:bg-usm-dark text-white shadow-sm transition disabled:opacity-50"
                                  >
                                    <Send className="w-3.5 h-3.5" />
                                    {ocupada
                                      ? 'Guardando...'
                                      : borrador.guardarEnJeff && borrador.texto.trim()
                                      ? 'Responder y guardar en Jeff'
                                      : 'Marcar como resuelta'}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              consulta.respuesta_profesor && (
                                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-700">
                                  <span className="font-semibold text-slate-800 block mb-1">
                                    Respuesta registrada:
                                  </span>
                                  {consulta.respuesta_profesor}
                                </div>
                              )
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })()
              )}
            </div>
          )}

          {/* OTRAS SUB-PESTAÑAS */}
          {subTab === 'jeff' && (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-2">
              <Bot className="w-10 h-10 text-usm-blue mx-auto" />
              <h3 className="text-base font-bold text-slate-800">Configuración de Jeff</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Aquí configuraremos las fechas de certámenes, requisitos de tareas y respuestas administrativas fijas.
              </p>
            </div>
          )}

          {subTab === 'socratico' && (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-2">
              <Sparkles className="w-10 h-10 text-usm-gold mx-auto" />
              <h3 className="text-base font-bold text-slate-800">Reglas Socráticas del Ramo</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Aquí el docente define el tono del tutor y las restricciones estrictas para no entregar respuestas resueltas.
              </p>
            </div>
          )}

          {subTab === 'analitica' && (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-2">
              <BarChart3 className="w-10 h-10 text-emerald-600 mx-auto" />
              <h3 className="text-base font-bold text-slate-800">Analítica Anónima de Dudas</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Aquí se desplegarán las métricas de qué temas están consultando los alumnos sin vulnerar su privacidad.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ======================================================== */}
      {/* VENTANA MODAL SUPERPUESTA PARA SUBIR ARCHIVO */}
      {/* ======================================================== */}
      {modalSubirAbierto && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full overflow-hidden">
            {/* Cabecera del Modal */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-usm-blue/10 text-usm-blue rounded-xl">
                  <UploadCloud className="w-5 h-5 text-usm-blue" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">Cargar Archivo al Repositorio</h3>
                  <p className="text-[11px] text-slate-500">Asignatura: {ramoActivo.codigo}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setModalSubirAbierto(false);
                  setArchivoParaSubir(null);
                }}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/60 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Formulario de Subida */}
            <form onSubmit={manejarSubidaModal} className="p-6 space-y-4">
              {/* Selección de Carpeta de Destino */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Carpeta de destino:
                </label>
                <select
                  value={carpetaDestinoSubida}
                  onChange={(e) => setCarpetaDestinoSubida(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-usm-blue font-mono font-medium"
                >
                  {carpetas.map((c) => (
                    <option key={c} value={c}>
                      📁 {c}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selector de Archivo */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Selecciona el documento:
                </label>
                <div
                  onClick={() => fileInputModalRef.current?.click()}
                  className="border-2 border-dashed border-slate-200 hover:border-usm-blue rounded-xl p-6 text-center cursor-pointer bg-slate-50/50 hover:bg-blue-50/30 transition-all"
                >
                  <input
                    ref={fileInputModalRef}
                    type="file"
                    accept=".pdf,.txt,.docx"
                    onChange={(e) => setArchivoParaSubir(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                  <FileText className="w-8 h-8 text-usm-blue mx-auto mb-2 opacity-80" />
                  {archivoParaSubir ? (
                    <div>
                      <p className="text-xs font-bold text-slate-800 truncate">
                        {archivoParaSubir.name}
                      </p>
                      <p className="text-[11px] text-emerald-600 font-semibold mt-0.5">
                        {(archivoParaSubir.size / (1024 * 1024)).toFixed(2)} MB · Listo para subir
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-semibold text-slate-700">
                        Haz clic para buscar o arrastra el archivo aquí
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">Formatos: PDF, TXT o DOCX</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Botones de Acción */}
              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setModalSubirAbierto(false);
                    setArchivoParaSubir(null);
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={subiendoArchivo || !archivoParaSubir}
                  className="px-4 py-2 rounded-xl bg-usm-blue hover:bg-usm-dark text-white text-xs font-bold shadow-md hover:shadow-lg transition disabled:opacity-50"
                >
                  {subiendoArchivo ? 'Subiendo e indexando...' : 'Subir e Indexar en RAG'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
};
