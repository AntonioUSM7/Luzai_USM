import React, { useState, useRef, useEffect } from 'react';
import { Send, HelpCircle, CheckCircle2, Sparkles, RotateCcw } from 'lucide-react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Ramo, MensajeChat } from '../../types';
import {
  enviarMensajeChat,
  enviarConsultaProfesor,
  resolverUrlApi,
  type MensajeHistorialApi,
} from '../../services/api';

const componentesMarkdown: Components = {
  img({ node: _node, src, alt, ...props }) {
    return (
      <img
        src={resolverUrlApi(typeof src === 'string' ? src : undefined)}
        alt={alt ?? ''}
        loading="lazy"
        {...props}
      />
    );
  },
  a({ node: _node, href, children, ...props }) {
    return (
      <a
        href={resolverUrlApi(typeof href === 'string' ? href : undefined)}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    );
  },
};

interface ChatWindowProps {
  ramo: Ramo;
  modoEmbebido?: boolean;
}

/**
 * Extrae las últimas preguntas guía (¿...?) de la respuesta del tutor socrático
 * para ofrecerlas como botones clicables sin consumir GPU adicional.
 */
function extraerPreguntasSugeridas(texto: string): string[] {
  const bloques = texto
    .split(/\n+/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#'));

  if (bloques.length === 0) return [];

  // Analiza los últimos bloques (donde el tutor deja las preguntas guía)
  const cola = bloques.slice(-3).join(' ');
  const matches = cola.match(/¿[^¿?\n]{8,220}\?/g) || [];

  const unicas: string[] = [];
  for (const m of matches) {
    const limpia = m.replace(/\*\*/g, '').replace(/\s+/g, ' ').trim();
    if (limpia && !unicas.includes(limpia)) {
      unicas.push(limpia);
    }
  }
  return unicas.slice(-3);
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ ramo, modoEmbebido = false }) => {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([]);
  const [entrada, setEntrada] = useState('');
  const [cargando, setCargando] = useState(false);
  const finChatRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const crearMensajeBienvenida = (): MensajeChat => ({
    id: `bienvenida-${ramo.codigo}-${Date.now()}`,
    autor: 'asistente',
    texto: modoEmbebido
      ? `Modo prueba docente activo para ${ramo.codigo} (${ramo.nombre}). Escribe cualquier pregunta como lo haría un estudiante para validar tus archivos RAG, FAQs de Jeff y reglas socráticas.`
      : `Hola, soy el tutor de ${ramo.codigo} (${ramo.nombre}). ¿En qué tema o duda te puedo orientar hoy?`,
    hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  });

  useEffect(() => {
    setMensajes([crearMensajeBienvenida()]);
  }, [ramo.codigo, ramo.nombre, modoEmbebido]);

  const manejarReiniciarChat = () => {
    if (cargando) return;
    setEntrada('');
    setMensajes([crearMensajeBienvenida()]);
    inputRef.current?.focus();
  };

  useEffect(() => {
    finChatRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensajes]);

  const enviarConsultaTexto = async (textoRaw: string) => {
    const texto = textoRaw.trim();
    if (!texto || cargando) return;

    const historial: MensajeHistorialApi[] = mensajes
      .filter(
        (m) =>
          !m.id.startsWith('bienvenida-') &&
          m.texto.trim().length > 0 &&
          !m.texto.startsWith('Error al comunicarse')
      )
      .slice(-6)
      .map((m) => ({
        rol: m.autor === 'usuario' ? 'user' : 'assistant',
        contenido: m.texto,
      }));

    const idUsuario = `user-${Date.now()}`;
    const idAsistente = `bot-${Date.now() + 1}`;
    const hora = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setMensajes((prev) => [
      ...prev,
      { id: idUsuario, autor: 'usuario', texto, hora },
      { id: idAsistente, autor: 'asistente', texto: '', hora },
    ]);
    setEntrada('');
    setCargando(true);

    try {
      await enviarMensajeChat(
        ramo.codigo,
        texto,
        (token) => {
          setMensajes((prev) =>
            prev.map((m) => (m.id === idAsistente ? { ...m, texto: m.texto + token } : m))
          );
        },
        (meta) => {
          setMensajes((prev) =>
            prev.map((m) =>
              m.id === idAsistente
                ? {
                    ...m,
                    canal: meta.canal ?? m.canal,
                    puedeEscalar: meta.puede_escalar ?? m.puedeEscalar,
                    motivoFallback: meta.motivo ?? m.motivoFallback,
                    preguntaOriginal: texto,
                    estadoEscalamiento: m.estadoEscalamiento ?? 'idle',
                    sugerencias: meta.sugerencias ?? m.sugerencias,
                  }
                : m
            )
          );
        },
        historial
      );
    } catch {
      setMensajes((prev) =>
        prev.map((m) =>
          m.id === idAsistente
            ? { ...m, texto: 'Error al comunicarse con el servidor. Intenta nuevamente.' }
            : m
        )
      );
    } finally {
      setCargando(false);
    }
  };

  const manejarEnvio = async (e: React.FormEvent) => {
    e.preventDefault();
    await enviarConsultaTexto(entrada);
  };

  const manejarEscalarProfesor = async (msg: MensajeChat) => {
    if (!msg.preguntaOriginal || msg.estadoEscalamiento === 'enviando' || msg.estadoEscalamiento === 'enviada') {
      return;
    }

    setMensajes((prev) =>
      prev.map((m) => (m.id === msg.id ? { ...m, estadoEscalamiento: 'enviando' } : m))
    );

    try {
      await enviarConsultaProfesor(
        ramo.codigo,
        msg.preguntaOriginal,
        msg.motivoFallback || 'sin_respaldo_rag'
      );
      setMensajes((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, estadoEscalamiento: 'enviada' } : m))
      );
    } catch {
      setMensajes((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, estadoEscalamiento: 'error' } : m))
      );
    }
  };

  const manejarUsarSugerencia = (pregunta: string) => {
    setEntrada(pregunta);
    inputRef.current?.focus();
  };

  const esRedes =
    ramo.codigo.toUpperCase().startsWith('TEL') ||
    ramo.nombre.toLowerCase().includes('red');
  const esMatematica = ramo.codigo.toUpperCase().startsWith('MAT');

  const etiquetaCanal = (canal?: MensajeChat['canal']) => {
    if (canal === 'JEFF_ADMIN') return 'Jeff · Información del curso';
    if (canal === 'FALLBACK_DOCENTE') return 'LuzIA · Revisión docente';
    return 'LuzIA · Tutor socrático';
  };

  return (
    <main className="flex-1 flex flex-col h-full bg-white overflow-hidden">
      {!modoEmbebido ? (
        <>
          {/* Franja superior continua con el Sidebar */}
          <div
            aria-hidden="true"
            className="h-1 w-full bg-gradient-to-r from-[#234E86] via-[#4378B8] to-[#83B7E8] shrink-0"
          />

          {/* Cabecera del ramo del alumno */}
          <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between gap-4 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <span className="font-mono text-[11px] font-bold px-2.5 py-0.5 rounded-sm bg-[#234E86] text-white tracking-wider shrink-0">
                {ramo.codigo}
              </span>
              <div className="min-w-0">
                <h2 className="font-display text-base font-bold text-slate-950 truncate">
                  {ramo.nombre}
                </h2>
                <p className="text-[11px] text-slate-500 truncate">{ramo.departamento}</p>
              </div>
            </div>

            <div className="hidden sm:flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>Tutor activo</span>
            </div>
          </header>
        </>
      ) : (
        <div className="bg-white border-b border-slate-200 px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] px-2 py-0.5 rounded-sm bg-[#EFF5FC] text-[#1E4478] border border-[#3A70B2]/25 shrink-0">
              Modo prueba
            </span>
            <p className="text-xs text-slate-500 truncate">
              Valida en tiempo real los documentos RAG, preguntas de Jeff y reglas socráticas configuradas.
            </p>
          </div>

          <button
            type="button"
            onClick={manejarReiniciarChat}
            disabled={cargando}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-sm border border-slate-200 bg-white hover:border-[#234E86] hover:text-[#234E86] text-slate-600 text-xs font-semibold transition disabled:opacity-50 shrink-0"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reiniciar chat</span>
          </button>
        </div>
      )}

      {/* Área de conversación con degradado suave y patrón geométrico sutil */}
      <div className="relative flex-1 overflow-y-auto bg-gradient-to-b from-[#FAFBFD] via-[#F3F8FD] to-[#E9F2FB]">
        {/* Patrón de fondo sutil fijo sobre el área del chat */}
        <div
          aria-hidden="true"
          className="pointer-events-none sticky top-0 h-0 w-full overflow-visible"
        >
          <div className="h-[calc(100vh-140px)] w-full relative overflow-hidden">
            {esRedes ? (
              <svg
                className="absolute inset-0 w-full h-full opacity-[0.06]"
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <pattern
                    id="chat-net-pattern"
                    width="96"
                    height="96"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M 16 24 L 56 16 L 84 48 L 44 76 Z M 56 16 L 44 76"
                      fill="none"
                      stroke="#1E4478"
                      strokeWidth="1"
                    />
                    <circle cx="16" cy="24" r="2.2" fill="#1E4478" />
                    <circle cx="56" cy="16" r="2.2" fill="#1E4478" />
                    <circle cx="84" cy="48" r="2.2" fill="#1E4478" />
                    <circle cx="44" cy="76" r="2.2" fill="#1E4478" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#chat-net-pattern)" />
              </svg>
            ) : esMatematica ? (
              <svg
                className="absolute inset-0 w-full h-full opacity-[0.055]"
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <pattern
                    id="chat-math-pattern"
                    width="48"
                    height="48"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M 48 0 L 0 0 0 48"
                      fill="none"
                      stroke="#1E4478"
                      strokeWidth="0.9"
                    />
                    <path
                      d="M 21 24 L 27 24 M 24 21 L 24 27"
                      fill="none"
                      stroke="#1E4478"
                      strokeWidth="0.9"
                    />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#chat-math-pattern)" />
              </svg>
            ) : (
              <svg
                className="absolute inset-0 w-full h-full opacity-[0.06]"
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <pattern
                    id="chat-dot-pattern"
                    width="32"
                    height="32"
                    patternUnits="userSpaceOnUse"
                  >
                    <circle cx="2" cy="2" r="1.2" fill="#1E4478" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#chat-dot-pattern)" />
              </svg>
            )}

            {/* Destello ambiental muy suave */}
            <div className="absolute -bottom-32 right-0 h-96 w-96 rounded-full bg-[#4378B8]/10 blur-3xl" />
          </div>
        </div>

        {/* Lista de mensajes centrada para lectura cómoda */}
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-8 space-y-5">
          {mensajes.map((msg, idx) => {
            const esUltimo = idx === mensajes.length - 1;
            const textoLimpio = (msg.texto || '').replace(/^📌\s*/, '');
            const sugerenciasBackend =
              msg.autor === 'asistente' &&
              !(cargando && esUltimo) &&
              Array.isArray(msg.sugerencias) &&
              msg.sugerencias.length > 0
                ? msg.sugerencias
                : [];
            const sugerencias =
              sugerenciasBackend.length > 0
                ? sugerenciasBackend
                : msg.autor === 'asistente' &&
                  msg.canal === 'TUTOR_SOCRATICO' &&
                  !(cargando && esUltimo)
                ? extraerPreguntasSugeridas(textoLimpio)
                : [];
            const esDesambiguacionJeff = sugerenciasBackend.length > 0 && msg.canal === 'JEFF_ADMIN';

            return (
              <div
                key={msg.id}
                className={`flex ${msg.autor === 'usuario' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-2xl rounded-sm px-5 py-4 text-sm leading-relaxed ${
                    msg.autor === 'usuario'
                      ? 'bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] text-white shadow-[0_6px_20px_-10px_rgba(30,68,120,0.45)]'
                      : 'bg-white/95 backdrop-blur-[2px] border border-slate-200/90 border-l-2 border-l-[#234E86] text-slate-800 shadow-[0_4px_18px_-12px_rgba(15,23,42,0.18)]'
                  }`}
                >
                  {/* Etiqueta de emisor y hora en asistente */}
                  {msg.autor === 'asistente' && (
                    <div className="flex items-center justify-between gap-4 mb-2 pb-1.5 border-b border-slate-100">
                      <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#3A70B2]">
                        {etiquetaCanal(msg.canal)}
                      </span>
                      <span className="font-mono text-[10px] text-slate-400">
                        {msg.hora}
                      </span>
                    </div>
                  )}

                  {msg.autor === 'usuario' ? (
                    <>
                      <p className="whitespace-pre-wrap">{textoLimpio}</p>
                      <span className="font-mono text-[10px] mt-2 block text-right text-blue-100/80">
                        {msg.hora}
                      </span>
                    </>
                  ) : (
                    <div className="markdown-content">
                      {textoLimpio ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm, remarkMath]}
                          rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
                          components={componentesMarkdown}
                        >
                          {textoLimpio}
                        </ReactMarkdown>
                      ) : (
                        <span className="font-mono text-xs text-slate-400">
                          Pensando respuesta...
                        </span>
                      )}
                    </div>
                  )}

                  {sugerencias.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                      <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-500">
                        <Sparkles className="w-3 h-3 text-[#3A70B2]" />
                        {esDesambiguacionJeff
                          ? 'Selecciona una opción'
                          : 'Preguntas sugeridas para seguir'}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {sugerencias.map((preg, pIdx) => (
                          <button
                            key={pIdx}
                            type="button"
                            onClick={() =>
                              esDesambiguacionJeff
                                ? enviarConsultaTexto(preg)
                                : manejarUsarSugerencia(preg)
                            }
                            disabled={cargando}
                            title={
                              esDesambiguacionJeff
                                ? 'Seleccionar esta planificación'
                                : 'Usar esta pregunta en el chat'
                            }
                            className={`text-left text-xs px-3 py-1.5 rounded-sm transition disabled:opacity-50 ${
                              esDesambiguacionJeff
                                ? 'bg-[#EFF5FC] hover:bg-[#1E4478] text-[#1E4478] hover:text-white border border-[#3A70B2]/40 font-semibold'
                                : 'bg-slate-50 hover:bg-[#EFF5FC] text-slate-700 hover:text-[#1E4478] border border-slate-200 hover:border-[#3A70B2]'
                            }`}
                          >
                            {preg}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {msg.autor === 'asistente' &&
                    msg.canal === 'FALLBACK_DOCENTE' &&
                    msg.puedeEscalar && (
                      <div className="mt-4 pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
                        {msg.estadoEscalamiento === 'enviada' ? (
                          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-sm">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Consulta enviada al profesor de {ramo.codigo}
                          </span>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => manejarEscalarProfesor(msg)}
                              disabled={msg.estadoEscalamiento === 'enviando'}
                              className="inline-flex items-center gap-1.5 text-xs font-semibold bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 px-3 py-1.5 rounded-sm transition disabled:opacity-50"
                            >
                              <HelpCircle className="w-3.5 h-3.5" />
                              {msg.estadoEscalamiento === 'enviando'
                                ? 'Enviando al profesor...'
                                : 'Enviar esta pregunta al profesor'}
                            </button>
                            {msg.estadoEscalamiento === 'error' && (
                              <span className="text-[11px] text-red-600">
                                No se pudo enviar. Intenta nuevamente.
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    )}
                </div>
              </div>
            );
          })}
          <div ref={finChatRef} />
        </div>
      </div>

      {/* Input de consulta */}
      <form
        onSubmit={manejarEnvio}
        className="px-6 py-4 bg-white border-t border-slate-200 shrink-0"
      >
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <input
            ref={inputRef}
            type="text"
            value={entrada}
            onChange={(e) => setEntrada(e.target.value)}
            placeholder={`Escribe tu consulta sobre ${ramo.codigo}...`}
            disabled={cargando}
            className="flex-1 bg-slate-50/80 border-b-2 border-slate-200 focus:border-[#234E86] focus:bg-white rounded-none px-3.5 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors"
          />
          <button
            type="submit"
            disabled={cargando || !entrada.trim()}
            className="bg-gradient-to-r from-[#1E4478] to-[#2B5D9E] hover:brightness-110 text-white font-display font-semibold px-5 py-3 rounded-sm text-xs tracking-wide flex items-center gap-2 transition disabled:opacity-45 shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Enviar</span>
          </button>
        </div>
      </form>
    </main>
  );
};
