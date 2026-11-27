import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router";

import PantallaCarga from "./components/ui/PantallaCarga";
import { RequiereRol, RequiereSesion, SoloInvitados } from "./auth/Guards";
import AppLayout from "./components/layout/AppLayout";
import { CajonCarritoProvider } from "./features/carrito/CajonCarrito";
import LoginPage from "./pages/auth/LoginPage";
import InicioPage from "./pages/InicioPage";
import NoEncontrado from "./pages/NoEncontrado";
import { CLIENTE } from "./utils/roles";

const RegistroPage = lazy(() => import("./pages/auth/RegistroPage"));
const CatalogoPage = lazy(() => import("./pages/CatalogoPage"));
const ProductoPage = lazy(() => import("./pages/ProductoPage"));
const CarritoPage = lazy(() => import("./pages/CarritoPage"));
const PedidoNuevoPage = lazy(() => import("./pages/PedidoNuevoPage"));
const PedidoPage = lazy(() => import("./pages/PedidoPage"));
const CuentaPage = lazy(() => import("./pages/CuentaPage"));

/**
 * Rutas. Todo exige sesión salvo login y registro (no hay catálogo público).
 * Carrito y pedidos: cliente (y administrador, que supera cualquier rol).
 */
export default function App() {
  return (
    <Suspense fallback={<PantallaCarga />}>
      <Routes>
        <Route element={<SoloInvitados />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registro" element={<RegistroPage />} />
        </Route>
  
        <Route element={<RequiereSesion />}>
          <Route
            element={
              <CajonCarritoProvider>
                <AppLayout />
              </CajonCarritoProvider>
            }
          >
            <Route index element={<InicioPage />} />
            <Route path="productos" element={<CatalogoPage />} />
            <Route path="productos/:id" element={<ProductoPage />} />
            <Route path="cuenta" element={<CuentaPage />} />
            <Route element={<RequiereRol roles={[CLIENTE]} />}>
              <Route path="carrito" element={<CarritoPage />} />
              <Route path="pedido" element={<PedidoNuevoPage />} />
              <Route path="pedidos/:id" element={<PedidoPage />} />
            </Route>
            <Route path="*" element={<NoEncontrado />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
