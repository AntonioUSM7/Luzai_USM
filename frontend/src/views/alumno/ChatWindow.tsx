import React, { useState, useRef, useEffect } from 'react';
import { Send, HelpCircle, CheckCircle2 } from 'lucide-react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Ramo, MensajeChat } from '../../types';
import { enviarMensajeChat, enviarConsultaProfesor, resolverUrlApi } from '../../services/api';

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
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ ramo }) => {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([]);
  const [entrada, setEntrada] = useState('');
  const [cargando, setCargando] = useState(false);
  const finChatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMensajes([
      {
        id: `bienvenida-${ramo.codigo}`,
        autor: 'asistente',
        texto: `Hola, soy el tutor de ${ramo.codigo} (${ramo.nombre}). ¿En qué tema o duda te puedo orientar hoy?`,
        hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  }, [ramo.codigo, ramo.nombre]);

  useEffect(() => {
    finChatRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensajes]);

  const manejarEnvio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entrada.trim() || cargando) return;

    const texto = entrada.trim();
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
                  }
                : m
            )
          );
        }
      );
    } catch {
      setMensajes((prev) =>
        prev.map((m) =>
          m.id === idAsistente
            ? { ...m, texto: '⚠️ Error al comunicarse con el servidor. Intenta nuevamente.' }
            : m
        )
      );
    } finally {
      setCargando(false);
    }
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

  return (
    <main className="flex-1 flex flex-col h-full bg-[#F4F6F9] overflow-hidden">
      {/* Cabecera del ramo del alumno (Estilo AULA USM) */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-usm-blue text-white">
              {ramo.codigo}
            </span>
            <h2 className="text-base font-bold text-slate-800">{ramo.nombre}</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{ramo.departamento}</p>
        </div>
      </header>

      {/* Lista de mensajes */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {mensajes.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.autor === 'usuario' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.autor === 'usuario'
                  ? 'bg-usm-blue text-white rounded-br-none shadow'
                  : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm'
              }`}
            >
              {msg.autor === 'usuario' ? (
                <p className="whitespace-pre-wrap">{msg.texto}</p>
              ) : (
                <div className="markdown-content">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
                    components={componentesMarkdown}
                  >
                    {msg.texto}
                  </ReactMarkdown>
                </div>
              )}
              {msg.autor === 'asistente' &&
                msg.canal === 'FALLBACK_DOCENTE' &&
                msg.puedeEscalar && (
                  <div className="mt-3 pt-2.5 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
                    {msg.estadoEscalamiento === 'enviada' ? (
                      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Consulta enviada al profesor de {ramo.codigo}
                      </span>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => manejarEscalarProfesor(msg)}
                          disabled={msg.estadoEscalamiento === 'enviando'}
                          className="inline-flex items-center gap-1.5 text-xs font-medium bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 px-3 py-1.5 rounded-lg transition disabled:opacity-50"
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
              <span
                className={`text-[10px] mt-1.5 block text-right ${
                  msg.autor === 'usuario' ? 'text-blue-100' : 'text-slate-400'
                }`}
              >
                {msg.hora}
              </span>
            </div>
          </div>
        ))}
        <div ref={finChatRef} />
      </div>

      {/* Input de consulta */}
      <form onSubmit={manejarEnvio} className="p-4 bg-white border-t border-slate-200 flex items-center gap-2">
        <input
          type="text"
          value={entrada}
          onChange={(e) => setEntrada(e.target.value)}
          placeholder={`Escribe tu consulta sobre ${ramo.codigo}...`}
          disabled={cargando}
          className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-usm-blue"
        />
        <button
          type="submit"
          disabled={cargando || !entrada.trim()}
          className="bg-usm-blue hover:bg-usm-dark text-white font-medium px-5 py-2.5 rounded-xl text-sm flex items-center gap-2 transition shadow disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          Enviar
        </button>
      </form>
    </main>
  );
};
