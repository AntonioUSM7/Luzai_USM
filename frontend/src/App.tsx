import React, { useEffect, useState } from 'react';
import { ChevronRight } from 'lucide-react';
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
  const [sidebarVisible, setSidebarVisible] = useState<boolean>(true);

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const listaRamos = await obtenerRamos();
        setRamos(listaRamos);
        // Inicializa en la vista general de "Mis Cursos"
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
        sidebarVisible={sidebarVisible}
        onToggleSidebar={() => setSidebarVisible((prev) => !prev)}
        onSeleccionarRamo={setRamoActivo}
        onCerrarSesion={() => setUsuario(null)}
      />

      {/* Botón flotante a la izquierda cuando la barra lateral está oculta */}
      {!sidebarVisible && (
        <button
          onClick={() => setSidebarVisible(true)}
          title="Mostrar barra lateral"
          className="fixed top-1/2 left-3 -translate-y-1/2 z-50 w-9 h-9 rounded-sm bg-white text-[#1E4478] shadow-md border border-slate-300 hover:bg-[#1E4478] hover:text-white hover:border-[#1E4478] transition-all flex items-center justify-center group"
        >
          <ChevronRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
        </button>
      )}

      {errorConexion ? (
        <div className="flex-1 flex items-center justify-center p-8 text-sm text-red-500">
          {errorConexion}
        </div>
      ) : usuario.rol === 'alumno' ? (
        ramoActivo ? (
          <ChatWindow ramo={ramoActivo} />
        ) : (
          <DocenteView
            ramos={ramos}
            ramoActivo={ramoActivo}
            onSeleccionarRamo={setRamoActivo}
          />
        )
      ) : (
        <DocenteView
          ramos={ramos}
          ramoActivo={ramoActivo}
          onSeleccionarRamo={setRamoActivo}
        />
      )}
    </div>
  );
}

export default App;
