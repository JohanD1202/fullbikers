// Direcciones de entrega (RF-11, API.md §7).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { direccionesApi } from "../../api/endpoints";

export const CLAVE_DIRECCIONES = ["direcciones"];

export function useDirecciones() {
  return useQuery({
    queryKey: CLAVE_DIRECCIONES,
    queryFn: async () => (await direccionesApi.listar()).direcciones,
  });
}

/** Tras crear, editar, marcar principal o eliminar: recargar la lista
 * (el backend puede desmarcar la principal anterior). */
function useMutacionDirecciones(fn) {
  const clienteQuery = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => clienteQuery.invalidateQueries({ queryKey: CLAVE_DIRECCIONES }),
  });
}

export const useCrearDireccion = () => useMutacionDirecciones((datos) => direccionesApi.crear(datos));
export const useActualizarDireccion = () => useMutacionDirecciones(({ id, cambios }) => direccionesApi.actualizar(id, cambios));
export const useEliminarDireccion = () => useMutacionDirecciones((id) => direccionesApi.eliminar(id));
