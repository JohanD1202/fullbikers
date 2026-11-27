import { useQuery } from "@tanstack/react-query";

import { catalogoApi } from "../../api/endpoints";

/** GET /principal: categorías activas + primera página de productos. */
export function usePrincipal() {
  return useQuery({
    queryKey: ["principal"],
    queryFn: () => catalogoApi.principal({ por_pagina: 8 }),
    staleTime: 60_000,
  });
}
