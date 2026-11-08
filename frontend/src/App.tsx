import React, { useEffect, useState } from 'react';
import { Login } from './components/Login';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './views/alumno/ChatWindow';
import { DocenteView } from './views/profesor/DocenteView';
import { Ramo, Usuario } from './types';
import { obtenerRamos } from './services/api';

export function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [ramos, setRamos] = useState<Ramo[]>([]);
  const [ramoActivo, setRamoActivo] = useState<Ramo | null>(null);
  const [errorConexion, setErrorConexion] = useState<string | null>(null);

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const listaRamos = await obtenerRamos();
        setRamos(listaRamos);
        if (listaRamos.length > 0) {
          setRamoActivo(listaRamos[0]);
        }
        setErrorConexion(null);
      } catch {
        setErrorConexion('No se pudo conectar con el servidor backend.');
      }
    };

    cargarDatos();
  }, []);

  // Vista 1: Login de ingreso
  if (!usuario) {
    return <Login onLogin={setUsuario} />;
  }

  // Vista 2: Portal una vez autenticado
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100">
      <Sidebar
        usuario={usuario}
        ramos={ramos}
        ramoActivo={ramoActivo}
        onSeleccionarRamo={setRamoActivo}
        onCerrarSesion={() => setUsuario(null)}
      />

      {errorConexion ? (
        <div className="flex-1 flex items-center justify-center p-8 text-sm text-red-500">
          {errorConexion}
        </div>
      ) : ramoActivo ? (
        usuario.rol === 'alumno' ? (
          <ChatWindow ramo={ramoActivo} />
        ) : (
          <DocenteView ramo={ramoActivo} />
        )
      ) : (
        <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
          Cargando datos...
        </div>
      )}
    </div>
  );
}

export default App;
