// Un módulo por recurso de la API. Solo endpoints que existen en el backend
// (backend/API.md §3 a §9). Las rutas se escriben relativas a VITE_API_URL.
import { solicitar } from "./client";

export const authApi = {
  registrar: (datos) => solicitar("/auth/register", { metodo: "POST", cuerpo: datos }),
  iniciarSesion: (datos) => solicitar("/auth/login", { metodo: "POST", cuerpo: datos }),
  cerrarSesion: () => solicitar("/auth/logout", { metodo: "POST" }),
  yo: () => solicitar("/auth/me"),
};

export const catalogoApi = {
  principal: ({ por_pagina } = {}) => solicitar("/principal", { parametros: { por_pagina } }),
  productos: ({ categoria, busqueda, pagina, por_pagina }, senal) =>
    solicitar("/productos", { parametros: { categoria, busqueda, pagina, por_pagina }, senal }),
  producto: (id) => solicitar(`/productos/${id}`),
};

export const perfilApi = {
  actualizar: (cambios) => solicitar("/perfil", { metodo: "PATCH", cuerpo: cambios }),
};

export const direccionesApi = {
  listar: () => solicitar("/direcciones"),
  crear: (datos) => solicitar("/direcciones", { metodo: "POST", cuerpo: datos }),
  actualizar: (id, cambios) => solicitar(`/direcciones/${id}`, { metodo: "PATCH", cuerpo: cambios }),
  eliminar: (id) => solicitar(`/direcciones/${id}`, { metodo: "DELETE" }),
};

export const carritoApi = {
  obtener: () => solicitar("/carrito"),
  agregar: ({ id_producto, id_variante, cantidad }) =>
    solicitar("/carrito/items", { metodo: "POST", cuerpo: { id_producto, id_variante, cantidad } }),
  actualizar: (idDetalle, cantidad) =>
    solicitar(`/carrito/items/${idDetalle}`, { metodo: "PATCH", cuerpo: { cantidad } }),
  retirar: (idDetalle) => solicitar(`/carrito/items/${idDetalle}`, { metodo: "DELETE" }),
};

export const pedidosApi = {
  registrar: ({ id_direccion, observaciones }) =>
    solicitar("/pedidos", { metodo: "POST", cuerpo: { id_direccion, observaciones: observaciones || null } }),
  obtener: (id) => solicitar(`/pedidos/${id}`),
};
