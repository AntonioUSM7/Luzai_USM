import React from 'react';
import { Ramo } from '../../types';
import { FileText, Settings } from 'lucide-react';

interface DocenteViewProps {
  ramo: Ramo;
}

export const DocenteView: React.FC<DocenteViewProps> = ({ ramo }) => {
  return (
    <main className="flex-1 p-8 bg-slate-50 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Cabecera del Ramo del Profesor */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-usm-navy text-usm-gold">
              {ramo.codigo}
            </span>
            <h1 className="text-xl font-bold text-slate-800">{ramo.nombre}</h1>
          </div>
          <p className="text-xs text-slate-500">{ramo.departamento} · {ramo.profesor}</p>
          <p className="text-sm text-slate-600 mt-3">{ramo.descripcion}</p>
        </div>

        {/* Recursos y Documentos del Ramo */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide flex items-center gap-2">
            <FileText className="w-4 h-4 text-usm-navy" />
            Recursos y Material de Estudio
          </h2>
          <ul className="divide-y divide-slate-100">
            {ramo.documentos.map((doc, idx) => (
              <li key={idx} className="py-2.5 flex items-center gap-2 text-sm text-slate-700">
                <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                <span>{doc}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Configuración del Comportamiento de la IA */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide flex items-center gap-2">
            <Settings className="w-4 h-4 text-usm-navy" />
            Configuración del Tutor IA (Base)
          </h2>
          <p className="text-xs text-slate-500">
            Reglas pedagógicas definidas para este ramo:
          </p>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 leading-relaxed">
            {ramo.reglas_socraticas}
          </div>
        </div>
      </div>
    </main>
  );
};
