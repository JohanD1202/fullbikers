import { Signpost } from "lucide-react";

import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";

export default function NoEncontrado() {
  return (
    <div className="contenedor">
      <EstadoVacio icono={Signpost} titulo="Esta página no existe" accion={<Boton to="/">Volver al inicio</Boton>}>
        Revisa la dirección o vuelve al inicio para seguir explorando.
      </EstadoVacio>
    </div>
  );
}
