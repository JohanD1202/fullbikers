import { ShieldOff } from "lucide-react";

import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";

/** 403 visual: el rol no permite esta sección. No cierra la sesión (API.md §1). */
export default function AccesoDenegado() {
  return (
    <div className="contenedor">
      <EstadoVacio icono={ShieldOff} titulo="Esta sección no está disponible para tu rol" accion={<Boton to="/">Volver al inicio</Boton>}>
        Si crees que deberías tener acceso, contacta al administrador de FullBikers.
      </EstadoVacio>
    </div>
  );
}
