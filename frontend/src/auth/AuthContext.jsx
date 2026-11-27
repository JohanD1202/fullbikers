// Sesión del usuario (backend/API.md §4, "Guía para React").
//
// - Token en sessionStorage; usuario en este contexto.
// - Al recargar: si hay token se llama a GET /auth/me para restaurar la sesión.
// - Cualquier 401 en una ruta protegida limpia la sesión y lleva a /login
//   (con "Su sesión expiró" si el código es token_expirado).
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";

import { registrarManejadorSesion, token } from "../api/client";
import { authApi } from "../api/endpoints";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const navegar = useNavigate();
  const clienteQuery = useQueryClient();
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(() => Boolean(token.obtener()));
  const [avisoLogin, setAvisoLogin] = useState(null);

  const limpiar = useCallback(() => {
    token.borrar();
    setUsuario(null);
    clienteQuery.clear();
  }, [clienteQuery]);

  useEffect(() => {
    registrarManejadorSesion((error) => {
      limpiar();
      setAvisoLogin(
        error.codigo === "token_expirado" ? "Su sesión expiró. Inicie sesión nuevamente." : "Debe iniciar sesión para continuar."
      );
      navegar("/login", { replace: true });
    });
    return () => registrarManejadorSesion(() => {});
  }, [limpiar, navegar]);

  // Restaurar la sesión al recargar la página.
  useEffect(() => {
    if (!token.obtener()) return;
    let vigente = true;
    authApi
      .yo()
      .then((datos) => vigente && setUsuario(datos.usuario))
      .catch(() => vigente && limpiar())
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [limpiar]);

  const iniciarSesion = useCallback(async (credenciales) => {
    const datos = await authApi.iniciarSesion(credenciales);
    token.guardar(datos.access_token);
    setUsuario(datos.usuario);
    setAvisoLogin(null);
    return datos.usuario;
  }, []);

  const cerrarSesion = useCallback(async () => {
    try {
      await authApi.cerrarSesion();
    } catch {
      // Aunque falle (red caída o token vencido), la sesión se cierra en el navegador.
    }
    limpiar();
    navegar("/login", { replace: true });
  }, [limpiar, navegar]);

  const valor = useMemo(
    () => ({ usuario, cargando, avisoLogin, setAvisoLogin, iniciarSesion, cerrarSesion, actualizarUsuario: setUsuario }),
    [usuario, cargando, avisoLogin, iniciarSesion, cerrarSesion]
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  return contexto;
}
