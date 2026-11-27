import { render } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import App from "../App";
import { AuthProvider } from "../auth/AuthContext";
import { AvisosProvider } from "../components/ui/Avisos";
import { token } from "../api/client";

export let ubicacionActual = null;
function Espia() {
  ubicacionActual = useLocation();
  return null;
}

/** Monta la aplicación completa en `ruta`; con `sesion` simula un token guardado. */
export function renderApp(ruta = "/", { sesion = true } = {}) {
  if (sesion) token.guardar("token-de-prueba");
  const clienteQuery = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={clienteQuery}>
      <MemoryRouter initialEntries={[ruta]}>
        <AvisosProvider>
          <AuthProvider>
            <App />
            <Espia />
          </AuthProvider>
        </AvisosProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}
