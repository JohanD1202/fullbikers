// Cliente HTTP de la API FullBikers (contratos: backend/API.md).
//
// - Añade Authorization: Bearer <token> en cada petición protegida.
// - Convierte toda respuesta de error en ApiError con el formato de la API:
//   {"error": {"codigo", "mensaje", "detalles"?}}.
// - Ante CUALQUIER 401 en una ruta protegida (todas salvo /auth/login y
//   /auth/register) borra el token y avisa al AuthContext, que lleva a /login.
//   Un 403 no cierra la sesión (API.md §1).

const CLAVE_TOKEN = "fullbikers_token";

export const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api").replace(/\/$/, "");

const RUTAS_PUBLICAS = new Set(["/auth/login", "/auth/register"]);

const MENSAJE_SIN_CONEXION = "No fue posible conectar con el servidor. Revise su conexión e intente de nuevo.";
const MENSAJE_GENERICO = "Ocurrió un error inesperado. Intente más tarde.";

export class ApiError extends Error {
  constructor({ status, codigo, mensaje, detalles = null, retryAfter = null }) {
    super(mensaje);
    this.name = "ApiError";
    this.status = status;
    this.codigo = codigo;
    this.detalles = detalles;
    this.retryAfter = retryAfter;
  }

  /** Errores por campo de un 400 "validacion": {campo: mensaje}. */
  get campos() {
    const campos = this.detalles?.campos;
    return campos && !Array.isArray(campos) ? campos : {};
  }
}

export const token = {
  obtener: () => sessionStorage.getItem(CLAVE_TOKEN),
  guardar: (valor) => sessionStorage.setItem(CLAVE_TOKEN, valor),
  borrar: () => sessionStorage.removeItem(CLAVE_TOKEN),
};

let alPerderSesion = () => {};

/** El AuthContext registra aquí qué hacer cuando la API responde 401. */
export function registrarManejadorSesion(fn) {
  alPerderSesion = fn;
}

function construirUrl(ruta, parametros) {
  const url = new URL(API_URL + ruta);
  if (parametros) {
    for (const [clave, valor] of Object.entries(parametros)) {
      if (valor !== undefined && valor !== null && valor !== "") url.searchParams.set(clave, String(valor));
    }
  }
  return url.toString();
}

export async function solicitar(ruta, { metodo = "GET", cuerpo, parametros, senal } = {}) {
  const cabeceras = { Accept: "application/json" };
  const actual = token.obtener();
  if (actual) cabeceras.Authorization = `Bearer ${actual}`;
  if (cuerpo !== undefined) cabeceras["Content-Type"] = "application/json";

  let respuesta;
  try {
    respuesta = await fetch(construirUrl(ruta, parametros), {
      method: metodo,
      headers: cabeceras,
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
      signal: senal,
    });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new ApiError({ status: 0, codigo: "sin_conexion", mensaje: MENSAJE_SIN_CONEXION });
  }

  if (respuesta.status === 204) return null;

  let datos = null;
  const texto = await respuesta.text();
  if (texto) {
    try {
      datos = JSON.parse(texto);
    } catch {
      datos = null;
    }
  }

  if (respuesta.ok) return datos;

  const error = new ApiError({
    status: respuesta.status,
    codigo: datos?.error?.codigo ?? "error_http",
    mensaje: datos?.error?.mensaje ?? MENSAJE_GENERICO,
    detalles: datos?.error?.detalles ?? null,
    retryAfter: Number(respuesta.headers.get("Retry-After")) || null,
  });

  if (respuesta.status === 401 && !RUTAS_PUBLICAS.has(ruta)) {
    token.borrar();
    alPerderSesion(error);
  }
  throw error;
}
