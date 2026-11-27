// Carrito (backend/API.md §8). Cada operación devuelve el carrito completo
// recalculado: se guarda directamente en la caché, sin GET posterior.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { carritoApi } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import { puedeComprar } from "../../utils/roles";

export const CLAVE_CARRITO = ["carrito"];

export const MOTIVOS = {
  producto_inactivo: "Este producto ya no está a la venta.",
  categoria_inactiva: "La categoría de este producto no está disponible.",
  variante_inactiva: "Esta talla o color ya no está a la venta.",
  sin_stock: "Se agotó. Retírelo para continuar.",
  stock_insuficiente: "No hay unidades suficientes para la cantidad elegida.",
};

export function useCarrito() {
  const { usuario } = useAuth();
  return useQuery({
    queryKey: CLAVE_CARRITO,
    queryFn: async () => (await carritoApi.obtener()).carrito,
    enabled: puedeComprar(usuario),
    staleTime: 30_000,
  });
}

function useMutacionCarrito(fn) {
  const clienteQuery = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (datos) => clienteQuery.setQueryData(CLAVE_CARRITO, datos.carrito),
    onError: (error) => {
      // El carrito pudo cambiar (convertido en pedido en otra pestaña, artículo retirado...).
      if (["carrito_no_modificable", "item_no_encontrado"].includes(error?.codigo)) {
        clienteQuery.invalidateQueries({ queryKey: CLAVE_CARRITO });
      }
    },
  });
}

export const useAgregarAlCarrito = () => useMutacionCarrito(carritoApi.agregar);
export const useActualizarCantidad = () => useMutacionCarrito(({ id, cantidad }) => carritoApi.actualizar(id, cantidad));
export const useRetirarDelCarrito = () => useMutacionCarrito((id) => carritoApi.retirar(id));
