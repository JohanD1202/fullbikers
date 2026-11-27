import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "./AuthContext";
import { tieneRol } from "../utils/roles";
import PantallaCarga from "../components/ui/PantallaCarga";
import AccesoDenegado from "../pages/AccesoDenegado";

/** Exige sesión. Sin usuario -> /login (recordando a dónde quería ir). */
export function RequiereSesion() {
  const { usuario, cargando } = useAuth();
  const ubicacion = useLocation();
  if (cargando) return <PantallaCarga />;
  if (!usuario) return <Navigate to="/login" replace state={{ desde: ubicacion.pathname + ubicacion.search }} />;
  return <Outlet />;
}

/** Exige uno de los roles (el administrador entra a todas). */
export function RequiereRol({ roles }) {
  const { usuario } = useAuth();
  if (!tieneRol(usuario, ...roles)) return <AccesoDenegado />;
  return <Outlet />;
}

/** Login y registro: si ya hay sesión, a la página que se pidió (o al inicio). */
export function SoloInvitados() {
  const { usuario, cargando } = useAuth();
  const { state } = useLocation();
  if (cargando) return <PantallaCarga />;
  if (usuario) return <Navigate to={destinoSeguro(state?.desde)} replace />;
  return <Outlet />;
}

/** Solo rutas internas ("/algo"), nunca URL externas ni "//dominio". */
export function destinoSeguro(desde) {
  return typeof desde === "string" && desde.startsWith("/") && !desde.startsWith("//") ? desde : "/";
}
