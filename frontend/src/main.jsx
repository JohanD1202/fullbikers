import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";

import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { AvisosProvider } from "./components/ui/Avisos";
import "./styles/global.css";

const clienteQuery = new QueryClient({
  defaultOptions: {
    queries: {
      // No reintentar errores del cliente (400-499): solo fallos de red o del servidor.
      retry: (intentos, error) => !(error?.status >= 400 && error?.status < 500) && intentos < 2,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <QueryClientProvider client={clienteQuery}>
      <BrowserRouter>
        <MotionConfig reducedMotion="user">
          <AvisosProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </AvisosProvider>
        </MotionConfig>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
