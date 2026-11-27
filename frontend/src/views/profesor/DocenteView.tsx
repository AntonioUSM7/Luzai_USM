import React, { useState, useEffect, useRef } from 'react';
import {
  Ramo,
  ArchivoRecurso,
  ConsultaProfesor,
  EstiloSocratico,
  ExtensionSocratica,
  FaqJeff,
} from '../../types';
import {
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  ChevronRight,
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
  ClipboardList,
  X,
  Plus,
  MessageSquare,
  MessageSquareMore,
  Send,
  Save,
  Search,
  Pencil,
  RefreshCw,
  Eye,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ChatWindow } from '../alumno/ChatWindow';
import { TareasJeffPanel } from './TareasJeffPanel';
import { AnaliticaDocentePanel } from './AnaliticaDocentePanel';
import {
  listarArchivosRamo,
  subirArchivosRamo,
  eliminarArchivoRamo,
  crearCarpetaRamo,
  eliminarCarpetaRamo,
  listarConsultasProfesor,
  responderConsultaProfesor,
  obtenerConfigSocratica,
  actualizarConfigSocratica,
  obtenerConfigFallback,
  actualizarConfigFallback,
  obtenerEstadoRag,
  reindexarRamo,
  listarFaqsJeff,
  crearFaqJeff,
  actualizarFaqJeff,
  eliminarFaqJeff,
  generarBorradorFaqIA,
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
  const [subTab, setSubTab] = useState<'archivos' | 'consultas' | 'jeff' | 'tareas' | 'socratico' | 'probar_ia' | 'analitica'>('archivos');

  // Estado del buzón de consultas escaladas por alumnos
  const [consultas, setConsultas] = useState<ConsultaProfesor[]>([]);
  const [cargandoConsultas, setCargandoConsultas] = useState<boolean>(false);
  const [filtroConsultas, setFiltroConsultas] = useState<'pendiente' | 'resuelta' | 'descartada' | 'todas'>('pendiente');
  const [borradoresRespuesta, setBorradoresRespuesta] = useState<
    Record<string, { texto: string; guardarEnJeff: boolean; palabrasClave: string; categoria: string }>
  >({});
  const [procesandoConsultaId, setProcesandoConsultaId] = useState<string | null>(null);

  // Estado de configuración socrática del ramo
  const [reglasSocraticas, setReglasSocraticas] = useState<string>('');
  const [estiloSocratico, setEstiloSocratico] = useState<EstiloSocratico>('equilibrado');
  const [extensionSocratica, setExtensionSocratica] = useState<ExtensionSocratica>('media');
  const [cargandoSocratica, setCargandoSocratica] = useState<boolean>(false);
  const [guardandoSocratica, setGuardandoSocratica] = useState<boolean>(false);

  // Estado de configuración de fallback estricto del ramo
  const [fallbackHabilitado, setFallbackHabilitado] = useState<boolean>(true);
  const [fallbackPermitirEscalar, setFallbackPermitirEscalar] = useState<boolean>(true);
  const [fallbackMsgSinRespaldo, setFallbackMsgSinRespaldo] = useState<string>('');
  const [fallbackMsgFueraFoco, setFallbackMsgFueraFoco] = useState<string>('');
  const [fallbackCanalAlt, setFallbackCanalAlt] = useState<string>('');
  const [guardandoFallback, setGuardandoFallback] = useState<boolean>(false);

  // Estado del apartado de Preguntas Guardadas (Jeff + RAG)
  const [faqsJeff, setFaqsJeff] = useState<FaqJeff[]>([]);
  const [cargandoFaqs, setCargandoFaqs] = useState<boolean>(false);
  const [busquedaFaqs, setBusquedaFaqs] = useState<string>('');
  const [paginaFaqs, setPaginaFaqs] = useState<number>(1);
  const [mostrarFormFaq, setMostrarFormFaq] = useState<boolean>(false);
  const [faqMinimizada, setFaqMinimizada] = useState<boolean>(false);
  const [faqVistaPrevia, setFaqVistaPrevia] = useState<boolean>(false);
  const [faqEditandoId, setFaqEditandoId] = useState<string | null>(null);
  const [faqPregunta, setFaqPregunta] = useState<string>('');
  const [faqRespuesta, setFaqRespuesta] = useState<string>('');
  const [faqCategoria, setFaqCategoria] = useState<string>('Consultas Resueltas');
  const [faqPalabrasClave, setFaqPalabrasClave] = useState<string>('');
  const [guardandoFaq, setGuardandoFaq] = useState<boolean>(false);
  const [generandoBorradorIA, setGenerandoBorradorIA] = useState<boolean>(false);
  const [fuentesBorradorIA, setFuentesBorradorIA] = useState<string[]>([]);
  const [faqArchivosIA, setFaqArchivosIA] = useState<string[]>([]);
  const [faqCarpetaAbiertaIA, setFaqCarpetaAbiertaIA] = useState<Record<string, boolean>>({});
  const [faqFiltroArchivosIA, setFaqFiltroArchivosIA] = useState<string>('');
  const [eliminandoFaqId, setEliminandoFaqId] = useState<string | null>(null);

  // Estado del gestor de archivos
  const [carpetas, setCarpetas] = useState<string[]>([]);
  const [carpetaSeleccionada, setCarpetaSeleccionada] = useState<string | null>(null); // null = raíz
  const [archivos, setArchivos] = useState<ArchivoRecurso[]>([]);
  const [cargando, setCargando] = useState<boolean>(false);
  const [fragmentosRag, setFragmentosRag] = useState<number | null>(null);
  const [reindexandoRag, setReindexandoRag] = useState<boolean>(false);

  // Estado de creación de carpeta (soporta subcarpetas anidadas)
  const [mostrarCrearCarpeta, setMostrarCrearCarpeta] = useState<boolean>(false);
  const [nombreNuevaCarpeta, setNombreNuevaCarpeta] = useState<string>('');
  const [carpetaPadreNueva, setCarpetaPadreNueva] = useState<string>('');
  const [creandoCarpeta, setCreandoCarpeta] = useState<boolean>(false);
  const [carpetasExpandidas, setCarpetasExpandidas] = useState<Record<string, boolean>>({});

  // Estado de la ventana modal superpuesta para subir archivos
  const [modalSubirAbierto, setModalSubirAbierto] = useState<boolean>(false);
  const [archivosParaSubir, setArchivosParaSubir] = useState<File[]>([]);
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
      const [resp, estadoRag] = await Promise.all([
        listarArchivosRamo(ramoActivo.codigo),
        obtenerEstadoRag(ramoActivo.codigo).catch(() => null),
      ]);
      setCarpetas(resp.carpetas);
      setArchivos(resp.archivos);
      setFragmentosRag(estadoRag ? estadoRag.fragmentos_indexados : null);
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

  const manejarReindexarRamo = async () => {
    if (!ramoActivo || reindexandoRag) return;
    setReindexandoRag(true);
    try {
      const res = await reindexarRamo(ramoActivo.codigo);
      mostrarMensaje('exito', res.mensaje || `Reindexación de ${ramoActivo.codigo} iniciada.`);
      setTimeout(() => {
        cargarDatosRamo();
      }, 2500);
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'No se pudo iniciar la reindexación.'
      );
    } finally {
      setReindexandoRag(false);
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

  const cargarConfigSocraticaRamo = async () => {
    if (!ramoActivo) return;
    setCargandoSocratica(true);
    try {
      const [cfg, cfgFb] = await Promise.all([
        obtenerConfigSocratica(ramoActivo.codigo),
        obtenerConfigFallback(ramoActivo.codigo).catch(() => null),
      ]);
      setReglasSocraticas(cfg.reglas_socraticas || '');
      setEstiloSocratico(cfg.estilo || 'equilibrado');
      setExtensionSocratica(cfg.extension || 'media');
      if (cfgFb) {
        setFallbackHabilitado(cfgFb.habilitado);
        setFallbackPermitirEscalar(cfgFb.permitir_escalar_profesor);
        setFallbackMsgSinRespaldo(cfgFb.mensaje_sin_respaldo || '');
        setFallbackMsgFueraFoco(cfgFb.mensaje_fuera_de_foco || '');
        setFallbackCanalAlt(cfgFb.canal_alternativo || '');
      }
    } catch (err) {
      console.error(err);
      mostrarMensaje('error', 'Error al cargar la configuración socrática.');
    } finally {
      setCargandoSocratica(false);
    }
  };

  const cargarFaqsJeffRamo = async () => {
    if (!ramoActivo) return;
    setCargandoFaqs(true);
    try {
      const lista = await listarFaqsJeff(ramoActivo.codigo);
      setFaqsJeff(lista);
    } catch (err) {
      console.error(err);
      mostrarMensaje('error', 'Error al cargar las preguntas guardadas de Jeff.');
    } finally {
      setCargandoFaqs(false);
    }
  };

  useEffect(() => {
    cargarDatosRamo();
    cargarConsultasRamo();
    cargarConfigSocraticaRamo();
    cargarFaqsJeffRamo();
    setCarpetaSeleccionada(null);
    setMostrarFormFaq(false);
    setFaqEditandoId(null);
    setBusquedaFaqs('');
  }, [ramoActivo?.codigo]);

  const abrirNuevaFaq = () => {
    setFaqEditandoId(null);
    setFaqPregunta('');
    setFaqRespuesta('');
    setFaqCategoria('Consultas Resueltas');
    setFaqPalabrasClave('');
    setFuentesBorradorIA([]);
    setFaqArchivosIA([]);
    setFaqMinimizada(false);
    setFaqVistaPrevia(false);
    setMostrarFormFaq(true);
  };

  const abrirEditarFaq = (faq: FaqJeff) => {
    setFaqEditandoId(faq.id);
    setFaqPregunta(faq.pregunta || '');
    setFaqRespuesta((faq.respuesta || '').replace(/^📌\s*/, ''));
    setFaqCategoria(faq.categoria || 'Consultas Resueltas');
    setFaqPalabrasClave((faq.palabras_clave || []).join(', '));
    setFuentesBorradorIA([]);
    setFaqArchivosIA([]);
    setFaqMinimizada(false);
    setFaqVistaPrevia(false);
    setMostrarFormFaq(true);
  };

  const minimizarFormFaq = () => {
    setFaqMinimizada(true);
  };

  const cancelarFormFaq = () => {
    setMostrarFormFaq(false);
    setFaqMinimizada(false);
    setFaqEditandoId(null);
    setFuentesBorradorIA([]);
    setFaqArchivosIA([]);
  };

  const manejarGuardarFaq = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo) return;

    const respuestaLimpia = faqRespuesta.trim();
    if (!respuestaLimpia) {
      mostrarMensaje('error', 'Debes escribir una respuesta oficial.');
      return;
    }

    const claves = faqPalabrasClave
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length >= 3);

    if (claves.length === 0 && !faqPregunta.trim()) {
      mostrarMensaje(
        'error',
        'Ingresa una pregunta de referencia o al menos una palabra clave (3+ caracteres).'
      );
      return;
    }

    setGuardandoFaq(true);
    try {
      const payload = {
        pregunta: faqPregunta.trim() || undefined,
        respuesta: respuestaLimpia,
        categoria: faqCategoria.trim() || 'Consultas Resueltas',
        palabras_clave: claves.length > 0 ? claves : undefined,
      };

      if (faqEditandoId) {
        const res = await actualizarFaqJeff(ramoActivo.codigo, faqEditandoId, payload);
        setFaqsJeff((prev) => prev.map((f) => (f.id === faqEditandoId ? res.faq : f)));
        mostrarMensaje(
          'exito',
          res.rag_sincronizado
            ? 'Pregunta actualizada en Jeff y sincronizada con el Tutor Socrático (RAG).'
            : 'Pregunta actualizada en Jeff (RAG se sincronizará al reindexar).'
        );
      } else {
        const res = await crearFaqJeff(ramoActivo.codigo, payload);
        setFaqsJeff((prev) => [...prev, res.faq]);
        mostrarMensaje(
          'exito',
          res.rag_sincronizado
            ? 'Pregunta guardada en Jeff y disponible para el Tutor Socrático (RAG).'
            : 'Pregunta guardada en Jeff (RAG se sincronizará al reindexar).'
        );
      }
      cancelarFormFaq();
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'No se pudo guardar la pregunta.'
      );
    } finally {
      setGuardandoFaq(false);
    }
  };

  const manejarEliminarFaq = async (faq: FaqJeff) => {
    if (!ramoActivo) return;
    const confirmar = window.confirm(
      `¿Eliminar esta pregunta guardada (${faq.pregunta || faq.id})? Dejará de responder en Jeff y en el Tutor Socrático.`
    );
    if (!confirmar) return;

    setEliminandoFaqId(faq.id);
    try {
      await eliminarFaqJeff(ramoActivo.codigo, faq.id);
      setFaqsJeff((prev) => prev.filter((f) => f.id !== faq.id));
      if (faqEditandoId === faq.id) {
        cancelarFormFaq();
      }
      mostrarMensaje('exito', 'Pregunta eliminada de Jeff y del índice RAG.');
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'No se pudo eliminar la pregunta.'
      );
    } finally {
      setEliminandoFaqId(null);
    }
  };

  const manejarGuardarConfigFallback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo) return;
    setGuardandoFallback(true);
    try {
      const actualizada = await actualizarConfigFallback(ramoActivo.codigo, {
        habilitado: fallbackHabilitado,
        permitir_escalar_profesor: fallbackPermitirEscalar,
        mensaje_sin_respaldo: fallbackMsgSinRespaldo,
        mensaje_fuera_de_foco: fallbackMsgFueraFoco,
        canal_alternativo: fallbackCanalAlt,
      });
      setFallbackMsgSinRespaldo(actualizada.mensaje_sin_respaldo);
      setFallbackMsgFueraFoco(actualizada.mensaje_fuera_de_foco);
      setFallbackCanalAlt(actualizada.canal_alternativo);
      mostrarMensaje('exito', `Configuración de fallback de ${ramoActivo.codigo} guardada.`);
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'No se pudo guardar la configuración de fallback.'
      );
    } finally {
      setGuardandoFallback(false);
    }
  };

  const abrirGuardarDudaEnJeff = (pregunta: string) => {
    setFaqEditandoId(null);
    setFaqPregunta(pregunta);
    setFaqRespuesta('');
    setFaqCategoria('Consultas Resueltas');
    setFaqPalabrasClave('');
    setFuentesBorradorIA([]);
    setFaqArchivosIA([]);
    setFaqMinimizada(false);
    setFaqVistaPrevia(false);
    setMostrarFormFaq(true);
    setSubTab('jeff');
  };

  const toggleArchivoFaqIA = (nombreArchivo: string) => {
    setFaqArchivosIA((prev) =>
      prev.includes(nombreArchivo)
        ? prev.filter((item) => item !== nombreArchivo)
        : [...prev, nombreArchivo]
    );
  };

  const manejarGenerarBorradorIA = async () => {
    if (!ramoActivo) return;
    const preguntaLimpia = faqPregunta.trim();
    if (!preguntaLimpia) {
      mostrarMensaje('error', 'Escribe primero una pregunta de referencia para generar el borrador.');
      return;
    }
    setGenerandoBorradorIA(true);
    setFuentesBorradorIA([]);
    try {
      const res = await generarBorradorFaqIA(ramoActivo.codigo, preguntaLimpia, faqArchivosIA);
      setFaqRespuesta(res.borrador);
      setFuentesBorradorIA(res.fuentes || []);
      if (Array.isArray(res.palabras_clave) && res.palabras_clave.length > 0) {
        setFaqPalabrasClave(res.palabras_clave.join(', '));
      }
      mostrarMensaje('exito', 'Borrador y palabras clave sugeridas generados con IA.');
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : 'No se pudo generar el borrador con IA';
      mostrarMensaje('error', mensaje);
    } finally {
      setGenerandoBorradorIA(false);
    }
  };

  const manejarGuardarConfigSocratica = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo) return;
    setGuardandoSocratica(true);
    try {
      await actualizarConfigSocratica(ramoActivo.codigo, {
        reglas_socraticas: reglasSocraticas,
        estilo: estiloSocratico,
        extension: extensionSocratica,
      });
      mostrarMensaje('exito', `Reglas socráticas de ${ramoActivo.codigo} guardadas correctamente.`);
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'No se pudo guardar la configuración socrática.'
      );
    } finally {
      setGuardandoSocratica(false);
    }
  };

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
        cargarFaqsJeffRamo();
        mostrarMensaje('exito', 'Respuesta guardada y agregada a las Preguntas Guardadas de Jeff y RAG.');
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

  // Crear nueva carpeta o subcarpeta
  const manejarCrearCarpeta = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo || !nombreNuevaCarpeta.trim()) return;

    setCreandoCarpeta(true);
    try {
      const rutaCreada = await crearCarpetaRamo(
        ramoActivo.codigo,
        nombreNuevaCarpeta.trim(),
        carpetaPadreNueva || null
      );
      setCarpetas((prev) => {
        // Asegurar que todos los ancestros existan en la lista ordenada
        const conjunto = new Set(prev);
        const partes = rutaCreada.split('/');
        let acumulado = '';
        for (const p of partes) {
          acumulado = acumulado ? `${acumulado}/${p}` : p;
          conjunto.add(acumulado);
        }
        return Array.from(conjunto).sort((a, b) => a.localeCompare(b));
      });
      // Expandir automáticamente todas las carpetas ancestras
      const partesAncestros = rutaCreada.split('/').slice(0, -1);
      if (partesAncestros.length > 0) {
        setCarpetasExpandidas((prev) => {
          const siguiente = { ...prev };
          let acc = '';
          for (const p of partesAncestros) {
            acc = acc ? `${acc}/${p}` : p;
            siguiente[acc] = true;
          }
          return siguiente;
        });
      }
      setCarpetaDestinoSubida(rutaCreada);
      setCarpetaSeleccionada(rutaCreada);
      setNombreNuevaCarpeta('');
      setMostrarCrearCarpeta(false);
      mostrarMensaje('exito', `Carpeta "${rutaCreada.replace(/\//g, ' / ')}" creada con éxito.`);
    } catch {
      mostrarMensaje('error', 'No se pudo crear la carpeta.');
    } finally {
      setCreandoCarpeta(false);
    }
  };

  const cerrarModalSubida = () => {
    setModalSubirAbierto(false);
    setArchivosParaSubir([]);
    if (fileInputModalRef.current) fileInputModalRef.current.value = '';
  };

  // Subir archivos desde la ventana modal
  const manejarSubidaModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ramoActivo || archivosParaSubir.length === 0) return;

    setSubiendoArchivo(true);
    try {
      const nuevos = await subirArchivosRamo(
        ramoActivo.codigo,
        archivosParaSubir,
        carpetaDestinoSubida
      );
      const clavesNuevas = new Set(nuevos.map((a) => `${a.carpeta}/${a.nombre}`));
      setArchivos((prev) => [
        ...nuevos,
        ...prev.filter((a) => !clavesNuevas.has(`${a.carpeta}/${a.nombre}`)),
      ]);
      cerrarModalSubida();
      mostrarMensaje(
        'exito',
        `${nuevos.length} archivo(s) subido(s) a "${carpetaDestinoSubida.replace(/\//g, ' / ')}".`
      );
    } catch (err) {
      mostrarMensaje(
        'error',
        err instanceof Error ? err.message : 'Ocurrió un error al subir los archivos.'
      );
    } finally {
      setSubiendoArchivo(false);
    }
  };

  // Eliminar archivo
  const manejarEliminarArchivo = async (archivo: ArchivoRecurso) => {
    if (!ramoActivo) return;
    const seguro = window.confirm(
      `¿Estás seguro de eliminar el archivo "${archivo.nombre}" de "${archivo.carpeta.replace(/\//g, ' / ')}"?`
    );
    if (!seguro) return;

    try {
      await eliminarArchivoRamo(ramoActivo.codigo, archivo.carpeta, archivo.nombre);
      setArchivos((prev) => prev.filter((a) => !(a.nombre === archivo.nombre && a.carpeta === archivo.carpeta)));
      mostrarMensaje('exito', `Archivo "${archivo.nombre}" eliminado correctamente.`);
    } catch {
      mostrarMensaje('error', 'No se pudo eliminar el archivo.');
    }
  };

  // Eliminar carpeta completa (incluyendo subcarpetas)
  const manejarEliminarCarpeta = async (e: React.MouseEvent, nombreCarpeta: string) => {
    e.stopPropagation();
    if (!ramoActivo) return;

    const prefijo = `${nombreCarpeta}/`;
    const cantArchivos = archivos.filter(
      (a) => a.carpeta === nombreCarpeta || a.carpeta.startsWith(prefijo)
    ).length;
    const cantSubcarpetas = carpetas.filter((c) => c.startsWith(prefijo)).length;
    const rutaLegible = nombreCarpeta.replace(/\//g, ' / ');

    const detalle =
      cantArchivos > 0 || cantSubcarpetas > 0
        ? `¿Estás seguro de eliminar "${rutaLegible}"${
            cantSubcarpetas > 0 ? `, sus ${cantSubcarpetas} subcarpeta(s)` : ''
          }${cantArchivos > 0 ? ` y ${cantArchivos} archivo(s)` : ''}? Esta acción es permanente.`
        : `¿Estás seguro de eliminar la carpeta vacía "${rutaLegible}"?`;

    const seguro = window.confirm(detalle);
    if (!seguro) return;

    try {
      await eliminarCarpetaRamo(ramoActivo.codigo, nombreCarpeta);
      setCarpetas((prev) => prev.filter((c) => c !== nombreCarpeta && !c.startsWith(prefijo)));
      setArchivos((prev) =>
        prev.filter((a) => a.carpeta !== nombreCarpeta && !a.carpeta.startsWith(prefijo))
      );
      if (
        carpetaSeleccionada === nombreCarpeta ||
        (carpetaSeleccionada && carpetaSeleccionada.startsWith(prefijo))
      ) {
        setCarpetaSeleccionada(null);
      }
      mostrarMensaje('exito', `Carpeta "${rutaLegible}" eliminada correctamente.`);
    } catch {
      mostrarMensaje('error', 'No se pudo eliminar la carpeta.');
    }
  };

  // Filtrado de archivos según carpeta seleccionada (incluye subcarpetas hijas)
  const archivosMostrados = archivos.filter((a) => {
    if (carpetaSeleccionada === null) return true;
    return a.carpeta === carpetaSeleccionada || a.carpeta.startsWith(`${carpetaSeleccionada}/`);
  });

  // Construcción de árbol jerárquico de carpetas/subcarpetas
  interface NodoCarpeta {
    nombre: string;
    ruta: string;
    hijos: NodoCarpeta[];
  }

  const arbolCarpetas = React.useMemo<NodoCarpeta[]>(() => {
    const mapa = new Map<string, NodoCarpeta>();
    const raices: NodoCarpeta[] = [];

    for (const rutaCompleta of [...carpetas].sort((a, b) => a.localeCompare(b))) {
      const partes = rutaCompleta.split('/').filter(Boolean);
      let acumulado = '';
      for (const parte of partes) {
        const rutaPadre = acumulado;
        acumulado = acumulado ? `${acumulado}/${parte}` : parte;
        if (!mapa.has(acumulado)) {
          const nodo: NodoCarpeta = { nombre: parte, ruta: acumulado, hijos: [] };
          mapa.set(acumulado, nodo);
          if (rutaPadre && mapa.has(rutaPadre)) {
            mapa.get(rutaPadre)!.hijos.push(nodo);
          } else if (!rutaPadre) {
            raices.push(nodo);
          }
        }
      }
    }
    return raices;
  }, [carpetas]);

  const abrirCrearSubcarpeta = (e: React.MouseEvent, rutaPadre: string) => {
    e.stopPropagation();
    setCarpetaPadreNueva(rutaPadre);
    setMostrarCrearCarpeta(true);
    setCarpetasExpandidas((prev) => ({ ...prev, [rutaPadre]: true }));
  };

  const toggleExpandirCarpeta = (e: React.MouseEvent, ruta: string) => {
    e.stopPropagation();
    setCarpetasExpandidas((prev) => ({ ...prev, [ruta]: !(prev[ruta] ?? true) }));
  };

  const renderizarNodosCarpeta = (nodos: NodoCarpeta[], nivel = 0): React.ReactNode => {
    return nodos.map((nodo) => {
      const activa = carpetaSeleccionada === nodo.ruta;
      const tieneHijos = nodo.hijos.length > 0;
      const expandida = carpetasExpandidas[nodo.ruta] ?? true;
      const cantArchivos = archivos.filter(
        (a) => a.carpeta === nodo.ruta || a.carpeta.startsWith(`${nodo.ruta}/`)
      ).length;

      return (
        <div key={nodo.ruta} className="space-y-1">
          <div className="relative flex items-center">
            <div className="w-3 border-t border-slate-200 mr-1.5 shrink-0" />

            <div
              onClick={() => setCarpetaSeleccionada(nodo.ruta)}
              className={`flex-1 flex items-center justify-between px-2 py-2 rounded-sm transition cursor-pointer group min-w-0 ${
                activa
                  ? 'bg-[#1B3E6E] text-white font-semibold'
                  : 'text-slate-700 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-1.5 min-w-0">
                {tieneHijos ? (
                  <button
                    type="button"
                    onClick={(e) => toggleExpandirCarpeta(e, nodo.ruta)}
                    className={`p-0.5 rounded-sm transition shrink-0 ${
                      activa
                        ? 'text-white/80 hover:bg-white/10'
                        : 'text-slate-400 hover:text-slate-700 hover:bg-slate-200/60'
                    }`}
                    title={expandida ? 'Contraer' : 'Expandir'}
                  >
                    {expandida ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </button>
                ) : (
                  <span className="w-4 shrink-0" />
                )}

                {activa ? (
                  <FolderOpen className="w-4 h-4 text-usm-gold shrink-0" />
                ) : (
                  <Folder className="w-4 h-4 text-slate-400 shrink-0" />
                )}
                <span className="truncate">{nodo.nombre}</span>
              </div>

              <div className="flex items-center gap-0.5 shrink-0 ml-1">
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-sm ${
                    activa ? 'bg-white/15 text-white' : 'bg-slate-100 text-slate-400'
                  }`}
                >
                  {cantArchivos}
                </span>

                <button
                  type="button"
                  onClick={(e) => abrirCrearSubcarpeta(e, nodo.ruta)}
                  title={`Crear subcarpeta dentro de "${nodo.nombre}"`}
                  className={`p-1 rounded-sm opacity-0 group-hover:opacity-100 transition ${
                    activa
                      ? 'text-white/75 hover:text-white hover:bg-white/15'
                      : 'text-slate-400 hover:text-[#234E86] hover:bg-blue-50'
                  }`}
                >
                  <FolderPlus className="w-3.5 h-3.5" />
                </button>

                <button
                  type="button"
                  onClick={(e) => manejarEliminarCarpeta(e, nodo.ruta)}
                  title={`Eliminar carpeta "${nodo.nombre}"`}
                  className={`p-1 rounded-sm opacity-0 group-hover:opacity-100 transition ${
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

          {tieneHijos && expandida && (
            <div className="pl-3 border-l border-slate-200 ml-5 space-y-1">
              {renderizarNodosCarpeta(nodo.hijos, nivel + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  // -------------------------------------------------------------
  // VISTA 1: PÁGINA DE INICIO "MIS CURSOS"
  // -------------------------------------------------------------
  if (!ramoActivo) {
    return (
      <main className="flex-1 bg-white overflow-y-auto">
        {/* Franja superior sutil en degradado armonizado con el Login */}
        <div
          aria-hidden="true"
          className="h-1 w-full bg-gradient-to-r from-[#234E86] via-[#4378B8] to-[#83B7E8]"
        />

        <div className="max-w-6xl mx-auto px-8 py-10 sm:px-12 space-y-10">
          <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-slate-200">
            <div>
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-[#3A70B2]">
                Portal Académico · LuzIA
              </span>
              <h1 className="font-display text-3xl font-bold tracking-tight text-slate-950 mt-1">
                Mis cursos
              </h1>
              <p className="text-sm text-slate-500 mt-1.5 max-w-2xl">
                Selecciona una asignatura para gestionar sus recursos, consultas escaladas y configuración del tutor socrático.
              </p>
            </div>

            <div className="font-mono text-[11px] uppercase tracking-[0.14em] text-slate-400">
              {ramos.length} {ramos.length === 1 ? 'asignatura' : 'asignaturas'}
            </div>
          </header>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-7">
            {ramos.map((ramo, index) => {
              const categoria = obtenerCategoria(ramo);
              const esRedes =
                ramo.codigo.toUpperCase().startsWith('TEL') ||
                ramo.nombre.toLowerCase().includes('red');
              const esMatematica = ramo.codigo.toUpperCase().startsWith('MAT');

              const gradienteTarjeta = esRedes
                ? 'from-[#1E4478] via-[#3469AD] to-[#6DA5DE]'
                : esMatematica
                ? 'from-[#28538A] via-[#477EC0] to-[#87BAE9]'
                : index % 2 === 0
                ? 'from-[#234E86] via-[#4378B8] to-[#83B7E8]'
                : 'from-[#1B3E6E] via-[#3869A8] to-[#74A9DF]';

              return (
                <article
                  key={ramo.codigo}
                  onClick={() => onSeleccionarRamo(ramo)}
                  className="group bg-white border border-slate-200 hover:border-[#3A70B2] rounded-sm overflow-hidden transition-all duration-200 cursor-pointer flex flex-col hover:shadow-[0_12px_30px_-14px_rgba(35,78,134,0.28)]"
                >
                  {/* Cabecera gráfica temática */}
                  <div
                    className={`h-40 relative p-5 flex flex-col justify-between overflow-hidden bg-gradient-to-br ${gradienteTarjeta}`}
                  >
                    {/* Arte vectorial temático por asignatura */}
                    {esRedes ? (
                      <svg
                        aria-hidden="true"
                        viewBox="0 0 360 160"
                        preserveAspectRatio="xMidYMid slice"
                        className="absolute inset-0 w-full h-full pointer-events-none"
                      >
                        {/* Retícula fina de fondo */}
                        <defs>
                          <pattern
                            id={`net-grid-${ramo.codigo}`}
                            width="28"
                            height="28"
                            patternUnits="userSpaceOnUse"
                          >
                            <path
                              d="M 28 0 L 0 0 0 28"
                              fill="none"
                              stroke="white"
                              strokeOpacity="0.08"
                              strokeWidth="1"
                            />
                          </pattern>
                        </defs>
                        <rect width="360" height="160" fill={`url(#net-grid-${ramo.codigo})`} />

                        {/* Enlaces de topología de red */}
                        <g stroke="white" strokeOpacity="0.32" strokeWidth="1.25" fill="none">
                          <line x1="48" y1="118" x2="132" y2="82" />
                          <line x1="132" y1="82" x2="222" y2="54" />
                          <line x1="222" y1="54" x2="312" y2="38" />
                          <line x1="132" y1="82" x2="210" y2="124" />
                          <line x1="222" y1="54" x2="210" y2="124" />
                          <line x1="210" y1="124" x2="306" y2="112" />
                          <line x1="222" y1="54" x2="306" y2="112" strokeDasharray="4 4" strokeOpacity="0.45" />
                          <line x1="76" y1="42" x2="132" y2="82" strokeDasharray="3 4" strokeOpacity="0.35" />
                          <line x1="76" y1="42" x2="222" y2="54" strokeOpacity="0.2" />
                        </g>

                        {/* Anillos de señal en el nodo central (switch/router) */}
                        <circle cx="222" cy="54" r="24" fill="none" stroke="white" strokeOpacity="0.14" strokeWidth="1" />
                        <circle cx="222" cy="54" r="14" fill="none" stroke="white" strokeOpacity="0.24" strokeWidth="1" />

                        {/* Nodos de red */}
                        <circle cx="76" cy="42" r="3" fill="white" fillOpacity="0.55" />
                        <circle cx="48" cy="118" r="3.5" fill="white" fillOpacity="0.6" />
                        <circle cx="132" cy="82" r="5" fill="#1E4478" stroke="white" strokeWidth="1.8" />
                        <circle cx="210" cy="124" r="4.5" fill="#2A5A98" stroke="white" strokeWidth="1.5" />
                        <circle cx="312" cy="38" r="3.5" fill="white" fillOpacity="0.75" />
                        <circle cx="306" cy="112" r="4" fill="#FFB000" fillOpacity="0.9" />

                        {/* Nodo principal resaltado */}
                        <circle cx="222" cy="54" r="6" fill="white" />
                        <circle cx="222" cy="54" r="2.5" fill="#234E86" />

                        {/* Paquete en tránsito */}
                        <rect x="171" y="64" width="6" height="6" transform="rotate(-17 174 67)" fill="#FFB000" fillOpacity="0.85" />
                      </svg>
                    ) : esMatematica ? (
                      <svg
                        aria-hidden="true"
                        viewBox="0 0 360 160"
                        preserveAspectRatio="xMidYMid slice"
                        className="absolute inset-0 w-full h-full pointer-events-none"
                      >
                        <defs>
                          <pattern
                            id={`math-grid-${ramo.codigo}`}
                            width="32"
                            height="32"
                            patternUnits="userSpaceOnUse"
                          >
                            <path
                              d="M 32 0 L 0 0 0 32"
                              fill="none"
                              stroke="white"
                              strokeOpacity="0.09"
                              strokeWidth="1"
                            />
                          </pattern>
                        </defs>
                        <rect width="360" height="160" fill={`url(#math-grid-${ramo.codigo})`} />
                        <path
                          d="M 0 115 Q 75 25, 165 88 T 360 55"
                          fill="none"
                          stroke="white"
                          strokeOpacity="0.32"
                          strokeWidth="1.75"
                        />
                        <path
                          d="M 0 135 Q 110 75, 210 105 T 360 35"
                          fill="none"
                          stroke="white"
                          strokeOpacity="0.16"
                          strokeWidth="1.25"
                          strokeDasharray="4 4"
                        />
                        <circle cx="165" cy="88" r="3.5" fill="#FFB000" fillOpacity="0.9" />
                      </svg>
                    ) : (
                      <div
                        aria-hidden="true"
                        className="absolute inset-0 opacity-[0.14] pointer-events-none"
                        style={{
                          backgroundImage:
                            'linear-gradient(to right, rgba(255, 255, 255, 0.45) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.45) 1px, transparent 1px)',
                          backgroundSize: '36px 36px',
                        }}
                      />
                    )}

                    {/* Etiqueta superior limpia */}
                    <div className="relative z-10 flex items-center justify-between">
                      <span className="font-mono text-[10px] font-semibold tracking-[0.16em] text-white/85 uppercase">
                        {categoria}
                      </span>
                      <span className="h-[2px] w-7 bg-usm-gold" />
                    </div>

                    {/* Código y acción inferior sobre el degradado */}
                    <div className="relative z-10 flex items-end justify-between">
                      <span className="font-display text-2xl font-extrabold tracking-tight text-white leading-none">
                        {ramo.codigo}
                      </span>
                      <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-white/85 flex items-center gap-1.5 group-hover:text-white transition">
                        <span>Abrir</span>
                        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                      </span>
                    </div>
                  </div>

                  {/* Cuerpo de la tarjeta */}
                  <div className="p-5 flex-1 flex flex-col justify-between gap-5">
                    <div>
                      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-slate-400">
                        2026-2 · Paralelo 200
                      </p>
                      <h2 className="font-display text-base font-bold text-slate-900 leading-snug mt-1 group-hover:text-[#234E86] transition-colors">
                        {ramo.nombre}
                      </h2>
                      <p className="text-xs text-slate-500 mt-2 line-clamp-2 leading-relaxed">
                        {ramo.descripcion}
                      </p>
                    </div>

                    <div className="pt-3.5 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1.5 text-slate-600 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        Operativo
                      </span>
                      <span className="font-mono text-slate-400">
                        {ramo.documentos.length} recursos RAG
                      </span>
                    </div>
                  </div>
                </article>
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
    <main className="flex-1 flex flex-col h-full bg-[#FAFBFC] overflow-hidden relative">
      {/* Franja superior en degradado */}
      <div
        aria-hidden="true"
        className="h-1 w-full bg-gradient-to-r from-[#234E86] via-[#4378B8] to-[#83B7E8] shrink-0"
      />

      {/* Cabecera del Ramo */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={() => onSeleccionarRamo(null)}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-[#234E86] transition shrink-0"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Mis cursos</span>
          </button>

          <div className="h-5 w-px bg-slate-200 shrink-0" />

          <div className="flex items-center gap-3 min-w-0">
            <span className="font-mono text-[11px] font-bold px-2.5 py-0.5 rounded-sm bg-[#234E86] text-white tracking-wider shrink-0">
              {ramoActivo.codigo}
            </span>
            <h1 className="font-display text-base font-bold text-slate-950 truncate">
              {ramoActivo.nombre}
            </h1>
          </div>
        </div>

        <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate-400 hidden sm:inline shrink-0">
          {ramoActivo.departamento}
        </span>
      </header>

      {/* Sub-Pestañas del Ramo (estilo minimalista con barra inferior en degradado) */}
      <nav className="bg-white border-b border-slate-200 px-8 flex gap-7 shrink-0 overflow-x-auto">
        <button
          onClick={() => setSubTab('archivos')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'archivos'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Folder className="w-4 h-4" />
          <span>Archivos del curso</span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded-sm">
            {archivos.length}
          </span>
          {subTab === 'archivos' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>

        <button
          onClick={() => setSubTab('consultas')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'consultas'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <MessageSquareMore className="w-4 h-4" />
          <span>Consultas de Alumnos</span>
          {consultas.filter((c) => c.estado === 'pendiente').length > 0 && (
            <span className="font-mono text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-800 font-bold rounded-sm">
              {consultas.filter((c) => c.estado === 'pendiente').length}
            </span>
          )}
          {subTab === 'consultas' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>

        <button
          onClick={() => setSubTab('jeff')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'jeff'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Bot className="w-4 h-4" />
          <span>Preguntas Guardadas (Jeff)</span>
          {faqsJeff.length > 0 && (
            <span className="font-mono text-[10px] px-1.5 py-0.5 bg-blue-50 text-[#234E86] font-bold rounded-sm">
              {faqsJeff.length}
            </span>
          )}
          {subTab === 'jeff' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>

        <button
          onClick={() => setSubTab('tareas')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'tareas'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <ClipboardList className="w-4 h-4" />
          <span>Tareas y Entregas</span>
          {subTab === 'tareas' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>

        <button
          onClick={() => setSubTab('socratico')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'socratico'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Reglas Socráticas</span>
          {subTab === 'socratico' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>

        <button
          onClick={() => setSubTab('probar_ia')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'probar_ia'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Probar Tutor IA</span>
          {subTab === 'probar_ia' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>

        <button
          onClick={() => setSubTab('analitica')}
          className={`relative py-3.5 text-xs font-semibold flex items-center gap-2 transition whitespace-nowrap ${
            subTab === 'analitica'
              ? 'text-[#234E86]'
              : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Analítica Anónima</span>
          {subTab === 'analitica' && (
            <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#234E86] to-[#5B97D4]" />
          )}
        </button>
      </nav>

      {/* Notificación flotante */}
      {notificacion && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-sm shadow-lg text-xs font-semibold flex items-center gap-2.5 border-l-4 bg-white transition-all ${
            notificacion.tipo === 'exito'
              ? 'text-slate-800 border-l-emerald-500 border border-slate-200'
              : 'text-slate-800 border-l-red-500 border border-slate-200'
          }`}
        >
          {notificacion.tipo === 'exito' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <X className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{notificacion.texto}</span>
        </div>
      )}

      {/* Contenido Principal */}
      {subTab === 'probar_ia' ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow ramo={ramoActivo} modoEmbebido />
        </div>
      ) : (
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* ======================================================== */}
          {/* SUB-PESTAÑA 1: EXPLORADOR DE CARPETAS Y ARCHIVOS DEL CURSO */}
          {/* ======================================================== */}
          {subTab === 'archivos' && (
            <div className="space-y-6">
              {/* Barra Superior */}
              <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-slate-200">
                <div>
                  <h2 className="font-display text-lg font-bold text-slate-950">
                    Estructura y archivos de {ramoActivo.codigo}
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Navega por las carpetas del ramo o crea nuevas divisiones temáticas.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5">
                  {fragmentosRag !== null && (
                    <span className="font-mono text-[10px] uppercase tracking-wider px-2.5 py-2 rounded-sm bg-slate-100 text-slate-600 border border-slate-200">
                      {fragmentosRag} fragmentos RAG
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={manejarReindexarRamo}
                    disabled={reindexandoRag}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-sm border border-slate-300 bg-white hover:border-[#234E86] hover:text-[#234E86] text-slate-700 text-xs font-semibold transition disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${reindexandoRag ? 'animate-spin' : ''}`} />
                    <span>{reindexandoRag ? 'Reindexando...' : 'Reindexar RAG'}</span>
                  </button>

                  <button
                    onClick={() => {
                      setCarpetaPadreNueva(carpetaSeleccionada || '');
                      setMostrarCrearCarpeta((prev) => !prev);
                    }}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-sm border border-slate-300 bg-white hover:border-[#234E86] hover:text-[#234E86] text-slate-700 text-xs font-semibold transition"
                  >
                    <FolderPlus className="w-4 h-4" />
                    <span>Nueva carpeta</span>
                  </button>

                  <button
                    onClick={() => {
                      if (carpetaSeleccionada) setCarpetaDestinoSubida(carpetaSeleccionada);
                      setModalSubirAbierto(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 rounded-sm bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-105 text-white font-display text-xs font-semibold transition active:scale-[0.99]"
                  >
                    <UploadCloud className="w-4 h-4" />
                    <span>Subir archivos</span>
                  </button>
                </div>
              </div>

              {/* Formulario rápido para crear nueva carpeta o subcarpeta */}
              {mostrarCrearCarpeta && (
                <form
                  onSubmit={manejarCrearCarpeta}
                  className="bg-white p-4 rounded-sm border-l-2 border-l-[#234E86] border border-slate-200 flex flex-wrap items-center gap-3"
                >
                  <FolderPlus className="w-4 h-4 text-[#234E86] shrink-0" />
                  <div className="w-full sm:w-56">
                    <select
                      value={carpetaPadreNueva}
                      onChange={(e) => setCarpetaPadreNueva(e.target.value)}
                      className="w-full text-xs bg-slate-50/70 border-b-2 border-slate-200 px-2.5 py-2 text-slate-700 font-mono focus:outline-none focus:border-[#234E86] focus:bg-white rounded-none transition-colors"
                      title="Ubicación de la nueva carpeta"
                    >
                      <option value="">Raíz (Carpeta_{ramoActivo.codigo})</option>
                      {carpetas.map((c) => (
                        <option key={c} value={c}>
                          {c.replace(/\//g, ' / ')}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <input
                      type="text"
                      placeholder={
                        carpetaPadreNueva
                          ? `Nombre de subcarpeta dentro de ${carpetaPadreNueva.replace(/\//g, ' / ')} (ej. Certamen 1)`
                          : 'Nombre de la nueva carpeta (ej. Laboratorios, Certamen 1)'
                      }
                      value={nombreNuevaCarpeta}
                      onChange={(e) => setNombreNuevaCarpeta(e.target.value)}
                      className="w-full text-xs bg-slate-50/70 border-b-2 border-slate-200 px-3 py-2 text-slate-900 focus:outline-none focus:border-[#234E86] focus:bg-white rounded-none transition-colors"
                      autoFocus
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={creandoCarpeta || !nombreNuevaCarpeta.trim()}
                    className="px-4 py-2 rounded-sm bg-[#234E86] text-white text-xs font-semibold hover:bg-[#1B3E6E] disabled:opacity-50 transition"
                  >
                    {creandoCarpeta ? 'Creando...' : 'Crear carpeta'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setMostrarCrearCarpeta(false)}
                    className="p-2 text-slate-400 hover:text-slate-700 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </form>
              )}

              {/* Layout Dividido: Árbol de Carpetas (Izquierda) + Archivos (Derecha) */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
                {/* ÁRBOL DE CARPETAS */}
                <div className="md:col-span-4 bg-white rounded-sm border border-slate-200 p-5 space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <span className="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">
                      Directorios
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {carpetas.length} carpetas
                    </span>
                  </div>

                  {/* Nodo Raíz: Carpeta_{CODIGO} */}
                  <div
                    onClick={() => setCarpetaSeleccionada(null)}
                    className={`flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer transition ${
                      carpetaSeleccionada === null
                        ? 'bg-[#234E86] text-white font-semibold'
                        : 'text-slate-800 hover:bg-slate-50'
                    }`}
                  >
                    <Folder className={`w-4 h-4 ${carpetaSeleccionada === null ? 'text-usm-gold' : 'text-[#3A70B2]'}`} />
                    <span className="truncate">Carpeta_{ramoActivo.codigo}</span>
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-sm ${carpetaSeleccionada === null ? 'bg-white/15 text-white' : 'bg-slate-100 text-slate-500'}`}>
                      {archivos.length}
                    </span>
                  </div>

                  {/* Ramas Recursivas de Carpetas y Subcarpetas */}
                  <div className="pl-3 border-l border-slate-200 ml-3 space-y-1">
                    {renderizarNodosCarpeta(arbolCarpetas)}
                  </div>
                </div>

                {/* EXPLORADOR DE ARCHIVOS DE LA CARPETA SELECCIONADA */}
                <div className="md:col-span-8 bg-white rounded-sm border border-slate-200 overflow-hidden">
                  {/* Encabezado del explorador */}
                  <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-slate-400">Ruta</span>
                      <span className="font-mono text-slate-600 font-medium">
                        Carpeta_{ramoActivo.codigo} /
                      </span>
                      <span className="font-mono text-[#234E86] font-bold">
                        {carpetaSeleccionada
                          ? carpetaSeleccionada.replace(/\//g, ' / ')
                          : 'Todas las carpetas'}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[11px] text-slate-400">
                        {archivosMostrados.length} archivo(s)
                      </span>

                      {carpetaSeleccionada && (
                        <button
                          onClick={(e) => manejarEliminarCarpeta(e, carpetaSeleccionada)}
                          title={`Eliminar carpeta "${carpetaSeleccionada}"`}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-xs font-semibold text-red-600 hover:bg-red-50 border border-red-200 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Eliminar carpeta</span>
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
                      <FolderOpen className="w-9 h-9 text-slate-300 mx-auto" />
                      <p className="font-display text-sm font-semibold text-slate-800">
                        {carpetaSeleccionada
                          ? `No hay archivos en la carpeta "${carpetaSeleccionada}"`
                          : 'No hay archivos en este curso aún'}
                      </p>
                      <p className="text-xs text-slate-400 max-w-sm mx-auto">
                        Presiona el botón "Subir archivos" para cargar uno o varios documentos y asignarlos a esta u otra carpeta.
                      </p>
                      <button
                        onClick={() => {
                          if (carpetaSeleccionada) setCarpetaDestinoSubida(carpetaSeleccionada);
                          setModalSubirAbierto(true);
                        }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-sm bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] text-white text-xs font-semibold hover:brightness-105 transition"
                      >
                        <UploadCloud className="w-4 h-4" />
                        <span>Subir archivos aquí</span>
                      </button>
                    </div>
                  ) : (
                    <ul className="divide-y divide-slate-100">
                      {archivosMostrados.map((archivo) => (
                        <li
                          key={`${archivo.carpeta}/${archivo.nombre}`}
                          className="px-5 py-4 flex items-center justify-between hover:bg-slate-50/70 transition"
                        >
                          <div className="flex items-center gap-3.5 min-w-0">
                            <div className="w-9 h-9 rounded-sm bg-slate-50 text-[#234E86] flex items-center justify-center shrink-0 border border-slate-200">
                              <FileText className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-slate-900 truncate">
                                {archivo.nombre}
                              </p>
                              <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-1">
                                <span className="inline-flex items-center gap-1 font-mono text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-sm">
                                  <Folder className="w-3 h-3 text-slate-400" />
                                  {archivo.carpeta.replace(/\//g, ' / ')}
                                </span>
                                <span>·</span>
                                <span className="font-mono text-[10px]">{archivo.tamano_legible}</span>
                                <span>·</span>
                                <span className="flex items-center gap-1 font-mono text-[10px]">
                                  <Clock className="w-3 h-3" />
                                  {archivo.fecha_modificacion}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 shrink-0">
                            {archivo.indexado_rag ? (
                              <span className="hidden sm:inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-sm">
                                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                Indexado RAG
                              </span>
                            ) : (
                              <span className="hidden sm:inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-sm">
                                <Clock className="w-3 h-3 text-amber-600" />
                                Pendiente RAG
                              </span>
                            )}

                            <button
                              onClick={() => manejarEliminarArchivo(archivo)}
                              title="Eliminar archivo"
                              className="p-2 rounded-sm text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
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
            <div className="space-y-6">
              <div className="pb-5 border-b border-slate-200 flex flex-wrap items-end justify-between gap-4">
                <div>
                  <h3 className="font-display text-lg font-bold text-slate-950">
                    Buzón de consultas escaladas ({ramoActivo.codigo})
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5 max-w-2xl">
                    Preguntas que ni Jeff ni el tutor socrático pudieron responder con respaldo y que los estudiantes enviaron para tu revisión.
                  </p>
                </div>
                <div className="flex items-center gap-4 border-b border-slate-200">
                  {(['pendiente', 'resuelta', 'descartada', 'todas'] as const).map((estado) => (
                    <button
                      key={estado}
                      type="button"
                      onClick={() => setFiltroConsultas(estado)}
                      className={`relative pb-2 text-xs font-semibold capitalize transition ${
                        filtroConsultas === estado
                          ? 'text-[#234E86]'
                          : 'text-slate-400 hover:text-slate-800'
                      }`}
                    >
                      {estado === 'todas' ? 'Todas' : `${estado}s`}
                      {filtroConsultas === estado && (
                        <span className="absolute bottom-[-1px] left-0 right-0 h-[2px] bg-[#234E86]" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {cargandoConsultas ? (
                <div className="bg-white p-10 rounded-sm border border-slate-200 text-center text-xs text-slate-500">
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
                      <div className="bg-white p-12 rounded-sm border border-slate-200 text-center space-y-2">
                        <MessageSquareMore className="w-8 h-8 text-slate-300 mx-auto" />
                        <p className="font-display text-sm font-semibold text-slate-800">
                          No hay consultas en esta categoría
                        </p>
                        <p className="text-xs text-slate-500">
                          Cuando un alumno escale una duda desde el chat, aparecerá aquí.
                        </p>
                      </div>
                    );
                  }

                  return (
                    <div className="space-y-4">
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
                            className="bg-white p-6 rounded-sm border border-slate-200 space-y-4"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <div className="space-y-1.5">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span
                                    className={`font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-sm ${
                                      consulta.estado === 'pendiente'
                                        ? 'bg-amber-100 text-amber-800'
                                        : consulta.estado === 'resuelta'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : 'bg-slate-200 text-slate-600'
                                    }`}
                                  >
                                    {consulta.estado}
                                  </span>
                                  <span className="font-mono text-[10px] px-2 py-0.5 rounded-sm bg-slate-100 text-slate-600">
                                    {consulta.motivo === 'fuera_de_foco'
                                      ? 'Fuera de foco'
                                      : 'Sin respaldo RAG'}
                                  </span>
                                  {consulta.guardada_en_jeff && (
                                    <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-blue-50 text-[#234E86] border border-blue-200">
                                      Guardada en Jeff ($0 GPU)
                                    </span>
                                  )}
                                </div>
                                <p className="font-display text-sm font-semibold text-slate-900">
                                  “{consulta.pregunta}”
                                </p>
                              </div>
                              <span className="font-mono text-[11px] text-slate-400">
                                {consulta.fecha_creacion.replace('T', ' ')}
                              </span>
                            </div>

                            {consulta.estado === 'pendiente' ? (
                              <div className="space-y-4 pt-3 border-t border-slate-100">
                                <div>
                                  <label className="block font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 mb-1.5">
                                    Respuesta del docente
                                  </label>
                                  <textarea
                                    rows={3}
                                    value={borrador.texto}
                                    onChange={(e) =>
                                      actualizarBorrador(consulta.id, { texto: e.target.value })
                                    }
                                    placeholder="Escribe una respuesta clara (si activas Jeff, esta respuesta se entregará automáticamente a futuros alumnos)..."
                                    className="w-full rounded-sm border border-slate-300 px-3 py-2.5 text-xs focus:outline-none focus:border-[#234E86] transition-colors"
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
                                    className="rounded-sm border-slate-300 text-[#234E86] focus:ring-[#234E86]"
                                  />
                                  <span className="font-medium">
                                    Guardar como FAQ de Jeff para responder futuras dudas iguales a $0 GPU
                                  </span>
                                </label>

                                {borrador.guardarEnJeff && (
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50/70 p-4 rounded-sm border border-slate-200">
                                    <div>
                                      <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
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
                                        placeholder="ej: subnetting, mascara, vlan"
                                        className="w-full rounded-sm border border-slate-300 px-2.5 py-2 text-xs bg-white focus:outline-none focus:border-[#234E86]"
                                      />
                                    </div>
                                    <div>
                                      <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
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
                                        className="w-full rounded-sm border border-slate-300 px-2.5 py-2 text-xs bg-white focus:outline-none focus:border-[#234E86]"
                                      />
                                    </div>
                                  </div>
                                )}

                                <div className="flex flex-wrap items-center justify-end gap-2.5">
                                  <button
                                    type="button"
                                    disabled={ocupada}
                                    onClick={() => manejarResponderConsulta(consulta, 'descartada')}
                                    className="px-3.5 py-2 rounded-sm text-xs font-semibold text-slate-600 hover:bg-slate-100 border border-slate-300 transition disabled:opacity-50"
                                  >
                                    Descartar
                                  </button>
                                  <button
                                    type="button"
                                    disabled={ocupada}
                                    onClick={() => manejarResponderConsulta(consulta, 'resuelta')}
                                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-sm text-xs font-semibold bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-105 text-white transition disabled:opacity-50"
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
                                <div className="bg-slate-50 border-l-2 border-l-[#234E86] border border-slate-200 rounded-sm p-3.5 text-xs text-slate-700">
                                  <span className="font-mono text-[10px] uppercase tracking-wider font-semibold text-slate-500 block mb-1">
                                    Respuesta registrada
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
            <div className="space-y-6">
              {/* Encabezado y acción principal */}
              <div className="pb-5 border-b border-slate-200 flex flex-wrap items-end justify-between gap-4">
                <div>
                  <h3 className="font-display text-lg font-bold text-slate-950">
                    Preguntas guardadas ({ramoActivo.codigo})
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5 max-w-2xl">
                    Jeff responde al instante por palabras clave ($0 GPU) y el Tutor Socrático también busca estas preguntas semánticamente vía RAG cuando un alumno pregunta con otras palabras.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={abrirNuevaFaq}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-sm bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] text-white font-display text-xs font-semibold hover:brightness-105 transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Nueva pregunta</span>
                </button>
              </div>

              {/* Modal de creación / edición de pregunta */}
              {mostrarFormFaq && !faqMinimizada && (
                <div
                  className="fixed inset-0 z-50 bg-slate-950/50 backdrop-blur-[2px] flex items-center justify-center p-4"
                  onClick={minimizarFormFaq}
                >
                  <div
                    className="bg-white rounded-sm shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="h-1 w-full bg-gradient-to-r from-[#234E86] via-[#4378B8] to-[#83B7E8] shrink-0" />
                    <form
                      onSubmit={manejarGuardarFaq}
                      className="p-6 space-y-4 overflow-y-auto"
                    >
                      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                        <h4 className="font-display text-sm font-bold text-slate-900">
                          {faqEditandoId ? 'Editar pregunta guardada' : 'Nueva pregunta guardada'}
                        </h4>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={minimizarFormFaq}
                            className="text-slate-400 hover:text-[#234E86] px-2 py-1 text-xs font-semibold rounded-sm hover:bg-slate-100 transition"
                            title="Minimizar a la barra inferior"
                          >
                            Minimizar
                          </button>
                          <button
                            type="button"
                            onClick={cancelarFormFaq}
                            className="text-slate-400 hover:text-slate-700 p-1 transition"
                            title="Descartar y cerrar"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                        Pregunta de referencia
                      </label>
                      <input
                        type="text"
                        value={faqPregunta}
                        onChange={(e) => setFaqPregunta(e.target.value)}
                        placeholder="Ej: ¿Cuándo se entrega el informe del Laboratorio 1?"
                        className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                      />
                    </div>
                    <div>
                      <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                        Categoría
                      </label>
                      <input
                        type="text"
                        value={faqCategoria}
                        onChange={(e) => setFaqCategoria(e.target.value)}
                        placeholder="Ej: Fechas y Entregas, Consultas Resueltas"
                        className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                      />
                    </div>
                  </div>

                  {archivos.some((a) => a.indexado_rag) && (() => {
                    const filtroNorm = faqFiltroArchivosIA.trim().toLowerCase();
                    const indexados = archivos.filter((a) => a.indexado_rag);
                    const filtrados = filtroNorm
                      ? indexados.filter(
                          (a) =>
                            a.nombre.toLowerCase().includes(filtroNorm) ||
                            (a.carpeta || 'General').toLowerCase().includes(filtroNorm)
                        )
                      : indexados;

                    const porCarpeta = filtrados.reduce<Record<string, ArchivoRecurso[]>>((acc, item) => {
                      const key = item.carpeta || 'General';
                      if (!acc[key]) acc[key] = [];
                      acc[key].push(item);
                      return acc;
                    }, {});
                    const nombresCarpetas = Object.keys(porCarpeta).sort((a, b) => a.localeCompare(b));

                    return (
                      <div className="rounded-sm border border-slate-200 bg-white overflow-hidden">
                        {/* Cabecera del explorador */}
                        <div className="px-3 py-2.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <FolderOpen className="w-3.5 h-3.5 text-[#234E86]" />
                            <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                              Documentos para que lea la IA (opcional)
                            </span>
                            {faqArchivosIA.length > 0 && (
                              <span className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded-sm bg-[#234E86] text-white">
                                {faqArchivosIA.length} selec.
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="relative">
                              <Search className="w-3 h-3 text-slate-400 absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none" />
                              <input
                                type="text"
                                value={faqFiltroArchivosIA}
                                onChange={(e) => setFaqFiltroArchivosIA(e.target.value)}
                                placeholder="Filtrar archivo..."
                                className="pl-6 pr-2 py-1 text-[11px] bg-white border border-slate-200 rounded-sm focus:outline-none focus:border-[#234E86] w-40"
                              />
                            </div>
                            {faqArchivosIA.length > 0 && (
                              <button
                                type="button"
                                onClick={() => setFaqArchivosIA([])}
                                className="text-[11px] font-medium text-[#234E86] hover:underline"
                              >
                                Limpiar
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Chips resumen de archivos seleccionados */}
                        {faqArchivosIA.length > 0 && (
                          <div className="px-3 py-2 bg-blue-50/60 border-b border-slate-200 flex flex-wrap gap-1.5">
                            {faqArchivosIA.map((nombre) => (
                              <span
                                key={nombre}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-[#234E86] text-white text-[11px] font-medium"
                              >
                                <FileText className="w-3 h-3 shrink-0" />
                                <span className="truncate max-w-[220px]">{nombre}</span>
                                <button
                                  type="button"
                                  onClick={() => toggleArchivoFaqIA(nombre)}
                                  className="ml-0.5 hover:text-blue-200"
                                  title="Quitar documento"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Árbol de carpetas y archivos */}
                        <div className="max-h-52 overflow-y-auto divide-y divide-slate-100">
                          {nombresCarpetas.length === 0 ? (
                            <p className="px-3 py-4 text-xs text-slate-400 text-center">
                              No se encontraron documentos indexados con ese filtro.
                            </p>
                          ) : (
                            nombresCarpetas.map((carpeta) => {
                              const lista = porCarpeta[carpeta];
                              const abierta = Boolean(filtroNorm) || Boolean(faqCarpetaAbiertaIA[carpeta]);
                              const cantSeleccionados = lista.filter((a) =>
                                faqArchivosIA.includes(a.nombre)
                              ).length;

                              return (
                                <div key={carpeta}>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setFaqCarpetaAbiertaIA((prev) => ({
                                        ...prev,
                                        [carpeta]: !prev[carpeta],
                                      }))
                                    }
                                    className="w-full px-3 py-2 flex items-center justify-between gap-2 text-left hover:bg-slate-50 transition"
                                  >
                                    <div className="flex items-center gap-2 min-w-0">
                                      {abierta ? (
                                        <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                      ) : (
                                        <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                      )}
                                      {abierta ? (
                                        <FolderOpen className="w-3.5 h-3.5 text-[#234E86] shrink-0" />
                                      ) : (
                                        <Folder className="w-3.5 h-3.5 text-[#234E86] shrink-0" />
                                      )}
                                      <span className="text-xs font-semibold text-slate-700 truncate">
                                        {carpeta}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                      {cantSeleccionados > 0 && (
                                        <span className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded-sm bg-blue-100 text-[#234E86]">
                                          {cantSeleccionados} selec.
                                        </span>
                                      )}
                                      <span className="font-mono text-[10px] text-slate-400">
                                        {lista.length} archivo{lista.length === 1 ? '' : 's'}
                                      </span>
                                    </div>
                                  </button>

                                  {abierta && (
                                    <ul className="bg-slate-50/40 divide-y divide-slate-100 border-t border-slate-100">
                                      {lista.map((archivo) => {
                                        const seleccionado = faqArchivosIA.includes(archivo.nombre);
                                        return (
                                          <li key={`${archivo.carpeta}/${archivo.nombre}`}>
                                            <label className="flex items-center justify-between gap-3 pl-9 pr-3 py-1.5 cursor-pointer hover:bg-blue-50/50 transition">
                                              <div className="flex items-center gap-2.5 min-w-0">
                                                <input
                                                  type="checkbox"
                                                  checked={seleccionado}
                                                  onChange={() => toggleArchivoFaqIA(archivo.nombre)}
                                                  className="h-3.5 w-3.5 rounded-sm border-slate-300 text-[#234E86] focus:ring-[#234E86] cursor-pointer shrink-0"
                                                />
                                                <FileText
                                                  className={`w-3.5 h-3.5 shrink-0 ${
                                                    seleccionado ? 'text-[#234E86]' : 'text-slate-400'
                                                  }`}
                                                />
                                                <span
                                                  className={`text-xs truncate ${
                                                    seleccionado
                                                      ? 'font-semibold text-[#234E86]'
                                                      : 'text-slate-700'
                                                  }`}
                                                >
                                                  {archivo.nombre}
                                                </span>
                                              </div>
                                              <span className="font-mono text-[10px] text-slate-400 shrink-0">
                                                {archivo.tamano_legible}
                                              </span>
                                            </label>
                                          </li>
                                        );
                                      })}
                                    </ul>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>

                        {/* Pie informativo */}
                        <div className="px-3 py-1.5 bg-slate-50/70 border-t border-slate-100 text-[10px] text-slate-500">
                          {faqArchivosIA.length > 0
                            ? `La IA leerá únicamente los ${faqArchivosIA.length} documento(s) seleccionado(s) para ahorrar tokens.`
                            : 'Si no marcas ningún archivo, la IA buscará automáticamente en los documentos más relevantes.'}
                        </div>
                      </div>
                    );
                  })()}

                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                      <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                        Respuesta oficial
                      </label>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => setFaqVistaPrevia((prev) => !prev)}
                          disabled={!faqRespuesta.trim() && !faqVistaPrevia}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm border text-[11px] font-semibold transition disabled:opacity-40 ${
                            faqVistaPrevia
                              ? 'border-[#234E86] bg-[#234E86] text-white'
                              : 'border-slate-200 bg-white text-slate-700 hover:border-[#234E86] hover:text-[#234E86]'
                          }`}
                          title="Alternar entre edición en texto y vista previa renderizada con LaTeX"
                        >
                          {faqVistaPrevia ? (
                            <>
                              <Pencil className="w-3 h-3" />
                              <span>Editar texto</span>
                            </>
                          ) : (
                            <>
                              <Eye className="w-3 h-3" />
                              <span>Vista previa</span>
                            </>
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={manejarGenerarBorradorIA}
                          disabled={generandoBorradorIA || !faqPregunta.trim()}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm border border-blue-200 bg-blue-50 text-[11px] font-semibold text-[#234E86] hover:bg-[#234E86] hover:text-white transition disabled:opacity-50"
                          title="Lee los documentos indexados del ramo y redacta un borrador editable"
                        >
                          {generandoBorradorIA ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Sparkles className="w-3 h-3" />
                          )}
                          <span>
                            {generandoBorradorIA ? 'Generando con IA...' : 'Generar borrador con IA'}
                          </span>
                        </button>
                      </div>
                    </div>

                    {faqVistaPrevia ? (
                      <div className="min-h-[168px] max-h-80 overflow-y-auto rounded-sm border border-blue-200 bg-slate-50/70 px-4 py-3 text-xs text-slate-800 markdown-content">
                        {faqRespuesta.trim() ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkMath]}
                            rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
                          >
                            {faqRespuesta}
                          </ReactMarkdown>
                        ) : (
                          <p className="text-slate-400 italic">
                            Aún no hay respuesta para previsualizar.
                          </p>
                        )}
                      </div>
                    ) : (
                      <textarea
                        rows={7}
                        value={faqRespuesta}
                        onChange={(e) => setFaqRespuesta(e.target.value)}
                        placeholder="Escribe la respuesta oficial que entregarán Jeff y el Tutor Socrático (soporta Markdown y LaTeX $...$)..."
                        className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                        required
                      />
                    )}
                    {fuentesBorradorIA.length > 0 && (
                      <p className="text-[11px] text-slate-500 mt-1">
                        Borrador generado a partir de:{' '}
                        <span className="font-mono text-slate-700">
                          {fuentesBorradorIA.join(', ')}
                        </span>
                        . Puedes modificarlo libremente antes de guardar.
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                      Palabras clave para Jeff (separadas por coma)
                    </label>
                    <input
                      type="text"
                      value={faqPalabrasClave}
                      onChange={(e) => setFaqPalabrasClave(e.target.value)}
                      placeholder="Ej: informe 1, entrega, plazo (si lo dejas vacío, se sugieren desde la pregunta)"
                      className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                    />
                    <p className="text-[11px] text-slate-400 mt-1">
                      Jeff interceptará consultas que contengan estas palabras clave; si no coinciden, el Tutor Socrático buscará por significado en RAG.
                    </p>
                  </div>

                  <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={cancelarFormFaq}
                      className="px-3.5 py-2 rounded-sm border border-slate-300 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={guardandoFaq}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-sm bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] text-white text-xs font-semibold hover:brightness-105 disabled:opacity-50 transition"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>
                        {guardandoFaq
                          ? 'Guardando...'
                          : faqEditandoId
                          ? 'Guardar cambios'
                          : 'Guardar pregunta'}
                      </span>
                    </button>
                  </div>
                    </form>
                  </div>
                </div>
              )}

              {/* Buscador y tarjetas paginadas */}
              <div className="bg-white p-5 rounded-sm border border-slate-200 space-y-5">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={busquedaFaqs}
                    onChange={(e) => {
                      setBusquedaFaqs(e.target.value);
                      setPaginaFaqs(1);
                    }}
                    placeholder="Buscar por pregunta, respuesta, categoría o palabras clave..."
                    className="w-full pl-9 pr-8 py-2.5 bg-slate-50/70 border border-slate-200 text-xs focus:outline-none focus:border-[#234E86] focus:bg-white rounded-sm transition-colors"
                  />
                  {busquedaFaqs && (
                    <button
                      type="button"
                      onClick={() => {
                        setBusquedaFaqs('');
                        setPaginaFaqs(1);
                      }}
                      title="Limpiar búsqueda"
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {cargandoFaqs ? (
                  <p className="text-xs text-slate-500 py-8 text-center">
                    Cargando preguntas guardadas...
                  </p>
                ) : (() => {
                  const FAQS_POR_PAGINA = 6;
                  const termino = busquedaFaqs.trim().toLowerCase();
                  const filtradas = !termino
                    ? faqsJeff
                    : faqsJeff.filter((f) => {
                        const bolsa = [
                          f.pregunta || '',
                          f.respuesta || '',
                          f.categoria || '',
                          ...(f.palabras_clave || []),
                        ]
                          .join(' ')
                          .toLowerCase();
                        return bolsa.includes(termino);
                      });

                  if (filtradas.length === 0) {
                    return (
                      <div className="py-10 text-center space-y-1.5">
                        <Bot className="w-8 h-8 text-slate-300 mx-auto" />
                        <p className="font-display text-sm font-semibold text-slate-800">
                          {faqsJeff.length === 0
                            ? 'Aún no hay preguntas guardadas para este ramo'
                            : 'No se encontraron preguntas con ese filtro'}
                        </p>
                        <p className="text-xs text-slate-500">
                          Crea una nueva pregunta arriba o guarda una respuesta desde Consultas de Alumnos o Analítica.
                        </p>
                      </div>
                    );
                  }

                  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / FAQS_POR_PAGINA));
                  const paginaActual = Math.min(paginaFaqs, totalPaginas);
                  const inicio = (paginaActual - 1) * FAQS_POR_PAGINA;
                  const visibles = filtradas.slice(inicio, inicio + FAQS_POR_PAGINA);

                  return (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                        {visibles.map((faq) => {
                          const textoLimpio = (faq.respuesta || '').replace(/^📌\s*/, '');
                          const keywords = faq.palabras_clave || [];
                          return (
                            <div
                              key={faq.id}
                              role="button"
                              tabIndex={0}
                              onClick={() => abrirEditarFaq(faq)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  abrirEditarFaq(faq);
                                }
                              }}
                              className="group flex flex-col justify-between p-4 rounded-sm border border-slate-200 bg-white hover:border-[#234E86] hover:shadow-sm transition cursor-pointer text-left space-y-2.5"
                            >
                              <div className="space-y-2">
                                <div className="flex items-start justify-between gap-2">
                                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-sm bg-blue-50 text-[#234E86] border border-blue-200 truncate max-w-[180px]">
                                    {faq.categoria || 'General'}
                                  </span>
                                  <button
                                    type="button"
                                    disabled={eliminandoFaqId === faq.id}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      manejarEliminarFaq(faq);
                                    }}
                                    title="Eliminar pregunta"
                                    className="p-1 rounded-sm text-slate-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-50 transition shrink-0"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>

                                <h4 className="font-display text-xs font-bold text-slate-900 group-hover:text-[#234E86] transition line-clamp-2 leading-snug">
                                  {faq.pregunta || faq.id}
                                </h4>

                                <p className="text-[11px] text-slate-600 leading-relaxed line-clamp-3">
                                  {textoLimpio}
                                </p>
                              </div>

                              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                                <div className="flex flex-wrap items-center gap-1 min-w-0">
                                  {keywords.slice(0, 2).map((kw) => (
                                    <span
                                      key={kw}
                                      className="font-mono text-[9px] px-1.5 py-0.5 rounded-sm bg-slate-100 text-slate-600 truncate max-w-[95px]"
                                    >
                                      {kw}
                                    </span>
                                  ))}
                                  {keywords.length > 2 && (
                                    <span className="font-mono text-[9px] text-slate-400">
                                      +{keywords.length - 2}
                                    </span>
                                  )}
                                </div>
                                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-400 group-hover:text-[#234E86] shrink-0">
                                  <Pencil className="w-3 h-3" />
                                  <span>Editar</span>
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Controles de paginación */}
                      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
                        <span className="font-mono text-[11px] text-slate-500">
                          Mostrando {inicio + 1}–{Math.min(inicio + FAQS_POR_PAGINA, filtradas.length)} de{' '}
                          {filtradas.length} pregunta{filtradas.length === 1 ? '' : 's'}
                        </span>
                        {totalPaginas > 1 && (
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              disabled={paginaActual <= 1}
                              onClick={() => setPaginaFaqs((p) => Math.max(1, p - 1))}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm border border-slate-200 text-xs font-medium text-slate-700 hover:border-[#234E86] hover:text-[#234E86] disabled:opacity-40 disabled:pointer-events-none transition"
                            >
                              <ArrowLeft className="w-3 h-3" />
                              <span>Anterior</span>
                            </button>
                            <span className="font-mono text-[11px] px-2 text-slate-600">
                              {paginaActual} / {totalPaginas}
                            </span>
                            <button
                              type="button"
                              disabled={paginaActual >= totalPaginas}
                              onClick={() => setPaginaFaqs((p) => Math.min(totalPaginas, p + 1))}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm border border-slate-200 text-xs font-medium text-slate-700 hover:border-[#234E86] hover:text-[#234E86] disabled:opacity-40 disabled:pointer-events-none transition"
                            >
                              <span>Siguiente</span>
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          )}

          {subTab === 'tareas' && (
            <TareasJeffPanel
              codigoRamo={ramoActivo.codigo}
              onNotify={mostrarMensaje}
            />
          )}

          {subTab === 'socratico' && (
            <div className="space-y-6">
              <form
                onSubmit={manejarGuardarConfigSocratica}
                className="bg-white p-7 rounded-sm border border-slate-200 space-y-7"
              >
                <div className="border-b border-slate-200 pb-5">
                  <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[#3A70B2]">
                    Configuración del modelo · Qwen3 8B
                  </span>
                  <h3 className="font-display text-lg font-bold text-slate-950 mt-1">
                    Reglas socráticas del tutor ({ramoActivo.codigo})
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Define cómo responde el modelo generativo cuando apoya a tus estudiantes con los apuntes del curso.
                  </p>
                </div>

                {cargandoSocratica ? (
                  <p className="text-xs text-slate-500 py-6 text-center">
                    Cargando configuración socrática...
                  </p>
                ) : (
                  <>
                    <div className="space-y-2.5">
                      <label className="block font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                        Estilo pedagógico
                      </label>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {(
                          [
                            {
                              id: 'estricto',
                              titulo: 'Estricto (Solo preguntas)',
                              desc: 'Responde con preguntas guía y pistas mínimas sin explicaciones largas.',
                            },
                            {
                              id: 'equilibrado',
                              titulo: 'Equilibrado (Recomendado)',
                              desc: 'Da una síntesis conceptual breve y cierra con 1–2 preguntas guía.',
                            },
                            {
                              id: 'paso_a_paso',
                              titulo: 'Paso a paso',
                              desc: 'Divide el problema en pasos pequeños y valida cada etapa con el alumno.',
                            },
                          ] as const
                        ).map((op) => (
                          <button
                            key={op.id}
                            type="button"
                            onClick={() => setEstiloSocratico(op.id)}
                            className={`text-left p-4 rounded-sm border transition ${
                              estiloSocratico === op.id
                                ? 'border-[#234E86] border-t-2 border-t-[#234E86] bg-blue-50/40'
                                : 'border-slate-200 hover:border-slate-300 bg-white'
                            }`}
                          >
                            <div className="font-display text-xs font-bold text-slate-900">{op.titulo}</div>
                            <p className="text-[11px] text-slate-500 mt-1.5 leading-relaxed">{op.desc}</p>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2.5">
                      <label className="block font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                        Extensión de respuesta
                      </label>
                      <div className="flex flex-wrap gap-3">
                        {(
                          [
                            { id: 'corta', label: 'Corta (1 párrafo breve o 3 viñetas)' },
                            { id: 'media', label: 'Media (1–2 párrafos estructurados)' },
                          ] as const
                        ).map((op) => (
                          <button
                            key={op.id}
                            type="button"
                            onClick={() => setExtensionSocratica(op.id)}
                            className={`px-4 py-2.5 rounded-sm text-xs font-semibold border transition ${
                              extensionSocratica === op.id
                                ? 'border-[#234E86] bg-[#234E86] text-white'
                                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                            }`}
                          >
                            {op.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="block font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                        Instrucciones y restricciones específicas del ramo
                      </label>
                      <textarea
                        rows={5}
                        value={reglasSocraticas}
                        onChange={(e) => setReglasSocraticas(e.target.value)}
                        placeholder="Ej.: Jamás entregues el resultado numérico final ni comandos completos. Usa analogías físicas y exige que el alumno identifique las condiciones de borde."
                        className="w-full rounded-sm border border-slate-300 px-3.5 py-2.5 text-xs leading-relaxed focus:outline-none focus:border-[#234E86]"
                      />
                    </div>

                    <div className="flex justify-end pt-4 border-t border-slate-100">
                      <button
                        type="submit"
                        disabled={guardandoSocratica}
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-sm font-display text-xs font-semibold bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-105 text-white transition disabled:opacity-50"
                      >
                        <Save className="w-4 h-4" />
                        {guardandoSocratica ? 'Guardando...' : 'Guardar configuración socrática'}
                      </button>
                    </div>
                  </>
                )}
              </form>

              <form
                onSubmit={manejarGuardarConfigFallback}
                className="bg-white p-7 rounded-sm border border-slate-200 space-y-5"
              >
                <div className="border-b border-slate-200 pb-4">
                  <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[#3A70B2]">
                    Guardrails · Respuesta sin respaldo
                  </span>
                  <h3 className="font-display text-base font-bold text-slate-950 mt-1">
                    Fallback estricto y escalamiento docente ({ramoActivo.codigo})
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Controla cómo responde el sistema cuando no encuentra respaldo en los apuntes o detecta una consulta fuera de foco.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer p-3 rounded-sm border border-slate-200 bg-slate-50/50">
                    <input
                      type="checkbox"
                      checked={fallbackHabilitado}
                      onChange={(e) => setFallbackHabilitado(e.target.checked)}
                      className="rounded-sm border-slate-300 text-[#234E86]"
                    />
                    <span className="font-medium">Activar fallback estricto ($0 GPU sin respaldo)</span>
                  </label>
                  <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer p-3 rounded-sm border border-slate-200 bg-slate-50/50">
                    <input
                      type="checkbox"
                      checked={fallbackPermitirEscalar}
                      onChange={(e) => setFallbackPermitirEscalar(e.target.checked)}
                      className="rounded-sm border-slate-300 text-[#234E86]"
                    />
                    <span className="font-medium">Permitir que el alumno envíe la duda al docente</span>
                  </label>
                </div>

                <div>
                  <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                    Mensaje cuando falta respaldo RAG
                  </label>
                  <textarea
                    rows={2}
                    value={fallbackMsgSinRespaldo}
                    onChange={(e) => setFallbackMsgSinRespaldo(e.target.value)}
                    className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                  />
                </div>

                <div>
                  <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                    Mensaje cuando la consulta está fuera de foco
                  </label>
                  <textarea
                    rows={2}
                    value={fallbackMsgFueraFoco}
                    onChange={(e) => setFallbackMsgFueraFoco(e.target.value)}
                    className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                  />
                </div>

                <div>
                  <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                    Canal alternativo sugerido
                  </label>
                  <input
                    type="text"
                    value={fallbackCanalAlt}
                    onChange={(e) => setFallbackCanalAlt(e.target.value)}
                    placeholder="Ej.: Foro de consultas en AULA USM"
                    className="w-full rounded-sm border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#234E86]"
                  />
                </div>

                <div className="flex justify-end pt-3 border-t border-slate-100">
                  <button
                    type="submit"
                    disabled={guardandoFallback}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-sm font-display text-xs font-semibold bg-[#234E86] hover:bg-[#1B3E6E] text-white transition disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    {guardandoFallback ? 'Guardando...' : 'Guardar configuración de fallback'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {subTab === 'analitica' && (
            <AnaliticaDocentePanel
              codigoRamo={ramoActivo.codigo}
              onGuardarEnJeff={abrirGuardarDudaEnJeff}
            />
          )}
        </div>
      </div>
      )}

      {/* ======================================================== */}
      {/* VENTANA MODAL SUPERPUESTA PARA SUBIR ARCHIVO */}
      {/* ======================================================== */}
      {modalSubirAbierto && (
        <div className="fixed inset-0 z-50 bg-slate-950/50 backdrop-blur-[2px] flex items-center justify-center p-4">
          <div className="bg-white rounded-sm shadow-2xl border border-slate-200 max-w-md w-full overflow-hidden">
            {/* Franja superior en degradado */}
            <div className="h-1 w-full bg-gradient-to-r from-[#234E86] via-[#4378B8] to-[#83B7E8]" />

            {/* Cabecera del Modal */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-display text-sm font-bold text-slate-950">
                  Cargar archivos al repositorio
                </h3>
                <p className="font-mono text-[10px] uppercase tracking-wider text-slate-400 mt-0.5">
                  Asignatura · {ramoActivo.codigo}
                </p>
              </div>
              <button
                onClick={cerrarModalSubida}
                className="p-1.5 text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Formulario de Subida */}
            <form onSubmit={manejarSubidaModal} className="p-6 space-y-5">
              {/* Selección de Carpeta de Destino */}
              <div>
                <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Carpeta de destino
                </label>
                <select
                  value={carpetaDestinoSubida}
                  onChange={(e) => setCarpetaDestinoSubida(e.target.value)}
                  className="w-full text-xs bg-slate-50/70 border-b-2 border-slate-200 rounded-none px-3 py-2.5 text-slate-800 focus:outline-none focus:border-[#234E86] font-mono font-medium"
                >
                  {carpetas.map((c) => (
                    <option key={c} value={c}>
                      {c.replace(/\//g, ' / ')}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selector de Archivos */}
              <div>
                <label className="block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Documentos
                </label>
                <div
                  onClick={() => fileInputModalRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    setArchivosParaSubir(Array.from(e.dataTransfer.files));
                  }}
                  className="border border-dashed border-slate-300 hover:border-[#234E86] rounded-sm p-6 text-center cursor-pointer bg-slate-50/50 hover:bg-blue-50/30 transition-all"
                >
                  <input
                    ref={fileInputModalRef}
                    type="file"
                    multiple
                    accept=".pdf,.txt,.md,.docx"
                    onChange={(e) => setArchivosParaSubir(Array.from(e.target.files || []))}
                    className="hidden"
                  />
                  <FileText className="w-7 h-7 text-[#3A70B2] mx-auto mb-2" />
                  {archivosParaSubir.length > 0 ? (
                    <div>
                      <p className="text-xs font-bold text-slate-900">
                        {archivosParaSubir.length} archivo(s) seleccionado(s)
                      </p>
                      <ul className="mt-2 space-y-0.5 text-left">
                        {archivosParaSubir.slice(0, 4).map((archivo, indice) => (
                          <li
                            key={`${archivo.name}-${indice}`}
                            className="font-mono text-[10px] text-slate-600 truncate"
                          >
                            {archivo.name}
                          </li>
                        ))}
                        {archivosParaSubir.length > 4 && (
                          <li className="font-mono text-[10px] text-slate-400">
                            +{archivosParaSubir.length - 4} más
                          </li>
                        )}
                      </ul>
                      <p className="font-mono text-[10px] text-emerald-600 font-semibold mt-2">
                        {(archivosParaSubir.reduce((total, archivo) => total + archivo.size, 0) / (1024 * 1024)).toFixed(2)} MB · Listos para subir
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-semibold text-slate-700">
                        Haz clic o arrastra los archivos aquí
                      </p>
                      <p className="font-mono text-[10px] text-slate-400 mt-1">
                        PDF, TXT, MD o DOCX · puedes seleccionar varios
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Botones de Acción */}
              <div className="pt-3 flex items-center justify-end gap-2.5 border-t border-slate-100">
                <button
                  type="button"
                  onClick={cerrarModalSubida}
                  className="px-4 py-2 rounded-sm text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={subiendoArchivo || archivosParaSubir.length === 0}
                  className="px-4 py-2 rounded-sm bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-105 text-white font-display text-xs font-semibold transition disabled:opacity-50"
                >
                  {subiendoArchivo ? 'Subiendo e indexando...' : 'Subir e indexar en RAG'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Barra flotante inferior para preguntas/borradores activos minimizados */}
      {ramoActivo && mostrarFormFaq && faqMinimizada && (
        <div className="fixed bottom-4 right-5 z-40 max-w-sm w-[calc(100vw-2.5rem)] sm:w-auto">
          <div className="flex items-center gap-3 bg-white border border-slate-300 border-t-2 border-t-[#234E86] rounded-sm shadow-xl px-3.5 py-2.5">
            <button
              type="button"
              onClick={() => {
                setSubTab('jeff');
                setFaqMinimizada(false);
              }}
              className="flex items-center gap-2.5 min-w-0 flex-1 text-left group"
              title="Abrir ventana para continuar editando o guardar"
            >
              <div className="w-7 h-7 rounded-sm bg-blue-50 text-[#234E86] flex items-center justify-center shrink-0">
                {generandoBorradorIA ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : faqRespuesta.trim() ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <Pencil className="w-3.5 h-3.5" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-900 group-hover:text-[#234E86] truncate max-w-[220px]">
                  {faqPregunta.trim() || (faqEditandoId ? 'Editando pregunta' : 'Nueva pregunta')}
                </p>
                <p className="font-mono text-[10px] text-slate-500">
                  {generandoBorradorIA
                    ? 'Generando borrador con IA...'
                    : faqRespuesta.trim()
                    ? 'Borrador listo · clic para guardar'
                    : 'Borrador activo · clic para abrir'}
                </p>
              </div>
            </button>
            <button
              type="button"
              onClick={cancelarFormFaq}
              title="Descartar borrador"
              className="p-1 rounded-sm text-slate-400 hover:text-red-600 hover:bg-red-50 transition shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </main>
  );
};
