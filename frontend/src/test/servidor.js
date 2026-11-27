// Doble de la API SOLO para pruebas automatizadas. Las respuestas siguen los
// contratos de backend/API.md; la aplicación nunca usa este archivo.
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const API = "http://127.0.0.1:5000/api";

export const cliente = { id_usuario: 7, nombre: "Ana", apellido: "Pérez", correo: "ana@ejemplo.com", telefono: null, rol: "cliente" };
export const empleado = { ...cliente, id_usuario: 8, nombre: "Eva", correo: "eva@ejemplo.com", rol: "empleado" };

export const categorias = [
  { id_categoria: 1, nombre: "Cascos", descripcion: "Cascos integrales", activo: true },
  { id_categoria: 2, nombre: "Guantes", descripcion: null, activo: true },
];

export const resumenCasco = {
  id_producto: 2, id_categoria: 1, categoria: "Cascos", nombre: "Casco abatible Urbano Pro", referencia: "CAS-ABA-002",
  descripcion: "Casco abatible con gafa solar interna.", marca: "RutaSegura", precio: "380000.00", imagen: null, stock_total: 5, disponible: true,
};

export const detalleCasco = {
  ...resumenCasco,
  variantes: [
    { id_variante: 4, id_producto: 2, talla: "M", color: "Blanco", compatibilidad: null, sku: "CAS-ABA-002-M-BLA", stock: 3, disponible: true },
    { id_variante: 5, id_producto: 2, talla: "L", color: "Blanco", compatibilidad: null, sku: "CAS-ABA-002-L-BLA", stock: 2, disponible: true },
    { id_variante: 6, id_producto: 2, talla: "XL", color: "Blanco", compatibilidad: null, sku: "CAS-ABA-002-XL-BLA", stock: 0, disponible: false },
  ],
};

export const carritoVacio = { id_carrito: null, estado: "abierto", items: [], cantidad_items: 0, cantidad_unidades: 0, total: "0.00", vacio: true, todos_disponibles: true };

export function carritoCon(cantidad = 1, extra = {}) {
  const subtotal = (380000 * cantidad).toFixed(2);
  return {
    id_carrito: 31, estado: "abierto",
    items: [{
      id_detalle_carrito: 88, id_producto: 2, id_variante: 5, nombre: "Casco abatible Urbano Pro", referencia: "CAS-ABA-002", marca: "RutaSegura",
      categoria: "Cascos", imagen: null, sku: "CAS-ABA-002-L-BLA", talla: "L", color: "Blanco", compatibilidad: null,
      cantidad, precio_unitario: "380000.00", subtotal, stock_disponible: 2, disponible: true, motivo_no_disponible: null, ...extra,
    }],
    cantidad_items: 1, cantidad_unidades: cantidad, total: subtotal, vacio: false, todos_disponibles: extra.disponible ?? true,
  };
}

export const direcciones = [
  { id_direccion: 12, departamento: "Valle del Cauca", municipio: "Tuluá", direccion: "Calle 26 # 30-15", complemento: "Apto 301", codigo_postal: "763021", principal: true },
  { id_direccion: 13, departamento: "Valle del Cauca", municipio: "Cali", direccion: "Carrera 5 # 10-20", complemento: null, codigo_postal: null, principal: false },
];

export const error = (status, codigo, mensaje, detalles) =>
  HttpResponse.json({ error: { codigo, mensaje, ...(detalles ? { detalles } : {}) } }, { status });

/** Manejadores básicos: sesión de `usuario` y catálogo con un producto. */
export function manejadoresBase(usuario = cliente) {
  return [
    http.get(`${API}/auth/me`, () => HttpResponse.json({ usuario })),
    http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
    http.get(`${API}/principal`, () =>
      HttpResponse.json({ categorias, productos: [resumenCasco], total_productos: 1, pagina: 1, por_pagina: 8, total_paginas: 1 })
    ),
    http.get(`${API}/productos`, () => HttpResponse.json({ productos: [resumenCasco], total_resultados: 1, pagina: 1, por_pagina: 12, total_paginas: 1 })),
    http.get(`${API}/productos/:id`, ({ params }) =>
      params.id === "2" ? HttpResponse.json(detalleCasco) : error(404, "producto_no_encontrado", "El producto no existe.")
    ),
    http.get(`${API}/carrito`, () => HttpResponse.json({ carrito: carritoVacio })),
    http.get(`${API}/direcciones`, () => HttpResponse.json({ direcciones })),
  ];
}

export const servidor = setupServer();
