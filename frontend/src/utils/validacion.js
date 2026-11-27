// Validación en el navegador con las MISMAS reglas del backend
// (services/usuario_service.py y services/direccion_service.py). Solo
// adelanta los mensajes: el backend vuelve a validar y su respuesta manda.

const PATRON_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PATRON_TELEFONO = /^\+?[0-9][0-9 ()-]{5,18}[0-9]$/;
const PATRON_CODIGO_POSTAL = /^[0-9]{4,10}$/;

const vacio = (v) => v === undefined || v === null || String(v).trim() === "";

export function textoObligatorio(valor, etiqueta, maximo) {
  if (vacio(valor)) return `${etiqueta} es obligatorio.`;
  if (String(valor).trim().length > maximo) return `${etiqueta} admite como máximo ${maximo} caracteres.`;
  return null;
}

export function textoOpcional(valor, etiqueta, maximo) {
  if (vacio(valor)) return null;
  if (String(valor).trim().length > maximo) return `${etiqueta} admite como máximo ${maximo} caracteres.`;
  return null;
}

export function correo(valor) {
  const limpio = String(valor ?? "").trim().toLowerCase();
  if (!limpio) return "El correo electrónico es obligatorio.";
  if (limpio.length > 254 || !PATRON_CORREO.test(limpio)) return "El correo electrónico no tiene un formato válido.";
  return null;
}

export function telefono(valor) {
  if (vacio(valor)) return null;
  if (!PATRON_TELEFONO.test(String(valor).trim()))
    return "El teléfono solo admite números, espacios, guiones, paréntesis y un + inicial (7 a 20 caracteres).";
  return null;
}

export function contrasena(valor) {
  if (!valor) return "La contraseña es obligatoria.";
  if (valor.length < 8 || valor.length > 128) return "La contraseña debe tener entre 8 y 128 caracteres.";
  if (!/\p{L}/u.test(valor) || !/\p{Nd}/u.test(valor)) return "La contraseña debe incluir al menos una letra y un número.";
  return null;
}

export function codigoPostal(valor) {
  if (vacio(valor)) return null;
  return PATRON_CODIGO_POSTAL.test(String(valor).trim()) ? null : "El código postal debe tener entre 4 y 10 dígitos.";
}

export function validarPersona(v) {
  return {
    nombre: textoObligatorio(v.nombre, "El nombre", 80),
    apellido: textoObligatorio(v.apellido, "El apellido", 80),
    correo: correo(v.correo),
    telefono: telefono(v.telefono),
  };
}

export function validarDireccion(v) {
  return {
    departamento: textoObligatorio(v.departamento, "El departamento", 60),
    municipio: textoObligatorio(v.municipio, "El municipio", 80),
    direccion: textoObligatorio(v.direccion, "La dirección", 150),
    complemento: textoOpcional(v.complemento, "El complemento", 100),
    codigo_postal: codigoPostal(v.codigo_postal),
  };
}

/** Quita las entradas sin error. */
export function soloErrores(errores) {
  return Object.fromEntries(Object.entries(errores).filter(([, m]) => m));
}
