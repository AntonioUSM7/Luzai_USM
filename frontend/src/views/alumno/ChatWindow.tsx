import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import { Ramo, MensajeChat } from '../../types';
import { enviarMensajeChat } from '../../services/api';

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
      await enviarMensajeChat(ramo.codigo, texto, (token) => {
        setMensajes((prev) =>
          prev.map((m) => (m.id === idAsistente ? { ...m, texto: m.texto + token } : m))
        );
      });
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

  return (
    <main className="flex-1 flex flex-col h-full bg-slate-50 overflow-hidden">
      {/* Cabecera del ramo del alumno */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-usm-navy text-usm-gold">
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
                  ? 'bg-usm-navy text-white rounded-br-none'
                  : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.texto}</p>
              <span
                className={`text-[10px] mt-1.5 block text-right ${
                  msg.autor === 'usuario' ? 'text-slate-300' : 'text-slate-400'
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
          className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-usm-navy"
        />
        <button
          type="submit"
          disabled={cargando || !entrada.trim()}
          className="bg-usm-navy hover:bg-usm-blue text-white font-medium px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 transition disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          Enviar
        </button>
      </form>
    </main>
  );
};
