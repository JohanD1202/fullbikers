// Roles funcionales (backend/models/usuario.py). El menú por rol es solo una
// ayuda visual: la API vuelve a verificar el permiso en cada llamada.
export const CLIENTE = "cliente";
export const EMPLEADO = "empleado";
export const ADMINISTRADOR = "administrador";

/** Igual que middleware/auth.py: el administrador supera cualquier comprobación. */
export function tieneRol(usuario, ...roles) {
  if (!usuario) return false;
  return usuario.rol === ADMINISTRADOR || roles.includes(usuario.rol);
}

/** Perfil editable, direcciones, carrito y pedidos: cliente y administrador. */
export const puedeComprar = (usuario) => tieneRol(usuario, CLIENTE);

export const NOMBRE_ROL = {
  [CLIENTE]: "Cliente",
  [EMPLEADO]: "Empleado",
  [ADMINISTRADOR]: "Administrador",
};
