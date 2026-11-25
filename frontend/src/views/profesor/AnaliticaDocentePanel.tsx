import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Bot,
  Clock,
  MessageSquare,
  PlusCircle,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { AnaliticaResumen, CanalChat } from '../../types';
import { obtenerAnaliticaRamo } from '../../services/api';

interface AnaliticaDocentePanelProps {
  codigoRamo: string;
  onGuardarEnJeff?: (pregunta: string) => void;
}

const formatoNumero = new Intl.NumberFormat('es-CL');

const etiquetaCanal = (canal: string) => {
  if (canal === 'JEFF_ADMIN') return 'Jeff administrativo';
  if (canal === 'FALLBACK_DOCENTE') return 'Derivación al docente';
  return 'Tutor socrático';
};

const colorBarraCanal = (canal: string) => {
  if (canal === 'JEFF_ADMIN') return 'bg-emerald-500';
  if (canal === 'FALLBACK_DOCENTE') return 'bg-amber-500';
  return 'bg-[#234E86]';
};

const formatoPorcentaje = (total: number, universo: number) =>
  universo > 0 ? `${Math.round((total / universo) * 100)}%` : '0%';

const porcentajeExacto = (total: number, universo: number) =>
  universo > 0 ? Math.max(0, Math.min(100, (total / universo) * 100)) : 0;

export const AnaliticaDocentePanel: React.FC<AnaliticaDocentePanelProps> = ({
  codigoRamo,
  onGuardarEnJeff,
}) => {
  const [dias, setDias] = useState<number>(30);
  const [canalFiltro, setCanalFiltro] = useState<'' | CanalChat>('');
  const [resumen, setResumen] = useState<AnaliticaResumen | null>(null);
  const [cargando, setCargando] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = async (
    rango: number = dias,
    canal: '' | CanalChat = canalFiltro
  ) => {
    setCargando(true);
    setError(null);
    try {
      setResumen(
        await obtenerAnaliticaRamo(
          codigoRamo,
          rango,
          canal || undefined,
          10
        )
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'No se pudo cargar la analítica del ramo.'
      );
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    cargar(dias, canalFiltro);
  }, [codigoRamo, dias, canalFiltro]);

  const total = resumen?.total_eventos ?? 0;
  const canalJeff =
    resumen?.por_canal.find((item) => item.canal === 'JEFF_ADMIN')?.total ?? 0;
  const canalTutor =
    resumen?.por_canal.find((item) => item.canal === 'TUTOR_SOCRATICO')?.total ?? 0;
  const canalFallback =
    resumen?.por_canal.find((item) => item.canal === 'FALLBACK_DOCENTE')?.total ?? 0;
  const diasConActividad = resumen?.por_dia.length ?? 0;

  return (
    <div className="space-y-6">
      <div className="pb-5 border-b border-slate-200 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h3 className="font-display text-lg font-bold text-slate-950">
            Analítica anónima de {codigoRamo}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 max-w-2xl">
            Métricas agregadas y preguntas más frecuentes. No se guardan nombres, RUT, correos, teléfonos, IPs ni identificadores de sesión.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 border border-slate-200 rounded-sm p-1 bg-white">
            {[7, 30, 90].map((rango) => (
              <button
                key={rango}
                type="button"
                onClick={() => setDias(rango)}
                className={`px-3 py-1.5 rounded-sm text-xs font-semibold transition ${
                  dias === rango
                    ? 'bg-[#234E86] text-white'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {rango} días
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => cargar()}
            disabled={cargando}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-sm border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:border-[#234E86] hover:text-[#234E86] disabled:opacity-50 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${cargando ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {cargando && !resumen ? (
        <div className="bg-white p-12 rounded-sm border border-slate-200 text-center text-xs text-slate-500">
          Cargando métricas del ramo...
        </div>
      ) : total === 0 ? (
        <div className="bg-white p-12 rounded-sm border border-slate-200 text-center space-y-3">
          <BarChart3 className="w-9 h-9 text-[#3A70B2] mx-auto" />
          <h3 className="font-display text-base font-bold text-slate-900">
            Aún no hay consultas registradas
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            Las métricas aparecerán cuando los estudiantes usen el tutor o Jeff en este ramo.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-sm border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  Consultas totales
                </span>
                <MessageSquare className="w-4 h-4 text-[#3A70B2]" />
              </div>
              <p className="font-display text-2xl font-bold text-slate-950 mt-2">
                {formatoNumero.format(total)}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                {diasConActividad} día(s) con actividad
              </p>
            </div>

            <div className="bg-white p-5 rounded-sm border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  Jeff administrativo
                </span>
                <Bot className="w-4 h-4 text-emerald-600" />
              </div>
              <p className="font-display text-2xl font-bold text-slate-950 mt-2">
                {formatoPorcentaje(canalJeff, total)}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                {formatoNumero.format(canalJeff)} consulta(s) sin GPU
              </p>
            </div>

            <div className="bg-white p-5 rounded-sm border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  Tutor socrático
                </span>
                <BarChart3 className="w-4 h-4 text-[#3A70B2]" />
              </div>
              <p className="font-display text-2xl font-bold text-slate-950 mt-2">
                {formatoPorcentaje(canalTutor, total)}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                {formatoNumero.format(canalTutor)} consulta(s) conceptuales
              </p>
            </div>

            <div className="bg-white p-5 rounded-sm border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  Derivación docente
                </span>
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              </div>
              <p className="font-display text-2xl font-bold text-slate-950 mt-2">
                {formatoPorcentaje(canalFallback, total)}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                {formatoNumero.format(canalFallback)} consulta(s) sin respaldo
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section className="bg-white rounded-sm border border-slate-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200">
                <h4 className="font-display text-sm font-bold text-slate-900">
                  Comparativa de carga por canal
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Ahorro de cómputo GPU (Jeff $0) frente a consultas pedagógicas y derivaciones.
                </p>
              </div>
              <div className="px-5 pt-4 pb-3 space-y-3 border-b border-slate-100">
                <div
                  className="h-3.5 w-full rounded-sm overflow-hidden bg-slate-100 flex"
                  aria-label="Distribución porcentual por canal"
                >
                  {(resumen?.por_canal ?? []).map((item) => {
                    const pct = porcentajeExacto(item.total, total);
                    if (pct <= 0) return null;
                    return (
                      <div
                        key={item.canal}
                        style={{ width: `${pct}%` }}
                        className={`${colorBarraCanal(item.canal)} transition-all`}
                        title={`${etiquetaCanal(item.canal)}: ${formatoPorcentaje(item.total, total)}`}
                      />
                    );
                  })}
                </div>
                <div className="flex flex-wrap gap-4 text-[11px] text-slate-600">
                  {(resumen?.por_canal ?? []).map((item) => (
                    <span key={item.canal} className="inline-flex items-center gap-1.5">
                      <span className={`w-2.5 h-2.5 rounded-xs ${colorBarraCanal(item.canal)}`} />
                      <span>{etiquetaCanal(item.canal)}:</span>
                      <strong className="font-mono text-slate-900">
                        {formatoPorcentaje(item.total, total)}
                      </strong>
                    </span>
                  ))}
                </div>
              </div>
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-5 py-2.5">Canal</th>
                    <th className="text-right px-5 py-2.5">Consultas</th>
                    <th className="text-right px-5 py-2.5">%</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(resumen?.por_canal ?? []).map((item) => (
                    <tr key={item.canal}>
                      <td className="px-5 py-3 font-medium text-slate-800">
                        {etiquetaCanal(item.canal)}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-700">
                        {formatoNumero.format(item.total)}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-500">
                        {formatoPorcentaje(item.total, total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="bg-white rounded-sm border border-slate-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200">
                <h4 className="font-display text-sm font-bold text-slate-900">
                  Motivos de derivación docente
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Consultas que quedaron fuera de foco o sin respaldo en los apuntes.
                </p>
              </div>
              {resumen?.por_motivo_fallback.length ? (
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                    <tr>
                      <th className="text-left px-5 py-2.5">Motivo</th>
                      <th className="text-right px-5 py-2.5">Consultas</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {resumen.por_motivo_fallback.map((item) => (
                      <tr key={item.motivo}>
                        <td className="px-5 py-3 text-slate-700">
                          {item.motivo === 'fuera_de_foco'
                            ? 'Fuera de foco'
                            : item.motivo === 'sin_respaldo_rag'
                              ? 'Sin respaldo RAG'
                              : item.motivo}
                        </td>
                        <td className="px-5 py-3 text-right font-mono text-slate-700">
                          {formatoNumero.format(item.total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="px-5 py-8 text-xs text-slate-500 text-center">
                  No hay derivaciones registradas en este rango.
                </p>
              )}
            </section>
          </div>

          <section className="bg-white rounded-sm border border-slate-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h4 className="font-display text-sm font-bold text-slate-900">
                  Preguntas más frecuentes
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Agrupadas por tópico en Jeff y por similitud léxica en Tutor Socrático / Derivación.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1 border border-slate-200 rounded-sm p-0.5 bg-slate-50">
                  {(
                    [
                      { id: '', label: 'Todos' },
                      { id: 'TUTOR_SOCRATICO', label: 'Tutor' },
                      { id: 'JEFF_ADMIN', label: 'Jeff' },
                      { id: 'FALLBACK_DOCENTE', label: 'Derivación' },
                    ] as const
                  ).map((op) => (
                    <button
                      key={op.id || 'todos'}
                      type="button"
                      onClick={() => setCanalFiltro(op.id)}
                      className={`px-2.5 py-1 rounded-sm text-[11px] font-semibold transition ${
                        canalFiltro === op.id
                          ? 'bg-[#234E86] text-white'
                          : 'text-slate-600 hover:bg-white'
                      }`}
                    >
                      {op.label}
                    </button>
                  ))}
                </div>
                <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  <Clock className="w-3.5 h-3.5" />
                  {formatoNumero.format(resumen?.latencia_promedio_ms ?? 0)} ms promedio
                </span>
              </div>
            </div>
            {resumen?.top_dudas.length ? (
              <ol className="divide-y divide-slate-100">
                {resumen.top_dudas.map((duda, indice) => (
                  <li
                    key={`${duda.texto}-${indice}`}
                    className="px-5 py-3.5 flex items-start gap-3"
                  >
                    <span className="font-mono text-[10px] font-bold w-5 h-5 rounded-sm bg-slate-100 text-slate-500 flex items-center justify-center shrink-0 mt-0.5">
                      {indice + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-slate-800 leading-relaxed">
                        {duda.texto}
                      </p>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="font-mono text-[10px] text-slate-400">
                          {etiquetaCanal(duda.canal || 'TUTOR_SOCRATICO')}
                        </span>
                        {duda.etiqueta && (
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-slate-100 text-slate-600">
                            {duda.etiqueta}
                          </span>
                        )}
                        {typeof duda.variantes === 'number' && duda.variantes > 1 && (
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-blue-50 text-[#234E86]">
                            {duda.variantes} variantes
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2.5 shrink-0">
                      {onGuardarEnJeff && duda.canal !== 'JEFF_ADMIN' && (
                        <button
                          type="button"
                          onClick={() => onGuardarEnJeff(duda.texto)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm border border-blue-200 bg-blue-50/70 text-[11px] font-semibold text-[#234E86] hover:bg-[#234E86] hover:text-white transition"
                          title="Crear una Pregunta Guardada de Jeff a partir de esta duda"
                        >
                          <PlusCircle className="w-3 h-3" />
                          <span>Guardar en Jeff</span>
                        </button>
                      )}
                      <span className="font-display text-sm font-bold text-[#234E86] min-w-[1.5rem] text-right">
                        {formatoNumero.format(duda.total)}
                      </span>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="px-5 py-8 text-xs text-slate-500 text-center">
                No hay preguntas registradas para este filtro.
              </p>
            )}
          </section>

          <section className="bg-white rounded-sm border border-slate-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h4 className="font-display text-sm font-bold text-slate-900">
                Actividad por día
              </h4>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Conteo diario de consultas, ordenado desde la fecha más reciente.
              </p>
            </div>
            {resumen?.por_dia.length ? (
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-mono text-[10px] uppercase tracking-wider sticky top-0">
                    <tr>
                      <th className="text-left px-5 py-2.5">Fecha</th>
                      <th className="text-right px-5 py-2.5">Consultas</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {resumen.por_dia.map((item) => (
                      <tr key={item.fecha}>
                        <td className="px-5 py-2.5 font-mono text-slate-600">
                          {item.fecha}
                        </td>
                        <td className="px-5 py-2.5 text-right font-mono text-slate-700">
                          {formatoNumero.format(item.total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="px-5 py-8 text-xs text-slate-500 text-center">
                No hay actividad diaria en este rango.
              </p>
            )}
          </section>

          <div className="flex items-start gap-2 bg-blue-50/60 border border-blue-200 rounded-sm px-4 py-3 text-[11px] text-slate-600">
            <ShieldCheck className="w-4 h-4 text-[#234E86] shrink-0 mt-0.5" />
            <p>
              Privacidad por diseño: el registro elimina correos, RUT, teléfonos, URLs e IPs del texto y no
              guarda identificadores de estudiantes. La vista solo entrega agregados.
            </p>
          </div>
        </>
      )}
    </div>
  );
};
