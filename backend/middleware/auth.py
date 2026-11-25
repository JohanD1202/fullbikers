"""Autenticación (JWT) y autorización por rol para los controladores.

Uso:

    from middleware.auth import requiere_autenticacion, requiere_rol, usuario_actual
    from models.usuario import EMPLEADO

    @bp.get("/api/auth/me")
    @requiere_autenticacion              # cualquier usuario activo
    def me(): ...

    @bp.get("/api/inventario")
    @requiere_rol(EMPLEADO)              # empleado (y administrador)
    def inventario(): ...

En cada petición protegida se comprueba, en este orden:
  1. Token presente, bien firmado y no expirado        -> si no, 401.
  2. El usuario del token existe y está activo (BD)     -> si no, 401.
  3. Su rol ACTUAL (leído de la BD) permite la operación -> si no, 403.
El administrador supera cualquier comprobación de rol.

Cierre de sesión: no hay revocación en el servidor. El frontend borra el
token; un token copiado sigue siendo válido hasta expirar (60 minutos), salvo
que el usuario sea desactivado (paso 2). Limitación aceptada para el alcance
académico.
"""
from functools import wraps

from flask import g
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request

from exceptions import AccesoDenegadoError, NoAutenticadoError, RecursoNoEncontradoError
from middleware.error_handlers import respuesta_error
from services import usuario_service

jwt = JWTManager()

MENSAJE_NO_AUTENTICADO = "Debe iniciar sesión para continuar."
MENSAJE_TOKEN_EXPIRADO = "Su sesión expiró. Inicie sesión nuevamente."
MENSAJE_ACCESO_DENEGADO = "No tiene permisos para realizar esta acción."


def init_app(app):
    jwt.init_app(app)

    # Todas las fallas del token responden con el formato de error de la API.
    @jwt.unauthorized_loader
    def _sin_token(_motivo):
        return respuesta_error("no_autenticado", MENSAJE_NO_AUTENTICADO, 401)

    @jwt.invalid_token_loader
    def _token_invalido(_motivo):
        return respuesta_error("no_autenticado", MENSAJE_NO_AUTENTICADO, 401)

    @jwt.expired_token_loader
    def _token_expirado(_cabecera, _datos):
        return respuesta_error("token_expirado", MENSAJE_TOKEN_EXPIRADO, 401)

    @jwt.revoked_token_loader
    @jwt.needs_fresh_token_loader
    @jwt.user_lookup_error_loader
    def _otro_rechazo(_cabecera, _datos):
        return respuesta_error("no_autenticado", MENSAJE_NO_AUTENTICADO, 401)


def _cargar_usuario_autenticado():
    """Valida el JWT y carga el usuario vigente en g.usuario."""
    verify_jwt_in_request()  # sus excepciones las responde JWTManager (401)
    identidad = get_jwt_identity()
    if not isinstance(identidad, str) or not identidad.isdigit():
        raise NoAutenticadoError(MENSAJE_NO_AUTENTICADO)
    usuario = usuario_service.obtener_usuario_activo(int(identidad))
    if usuario is None:
        # Usuario eliminado o desactivado después de emitir el token.
        raise NoAutenticadoError(MENSAJE_NO_AUTENTICADO)
    g.usuario = usuario
    return usuario


def tiene_rol(usuario, roles):
    """True si el usuario es administrador o su rol está en `roles`."""
    return usuario.es_administrador or usuario.rol in roles


def requiere_autenticacion(funcion):
    """Exige un usuario autenticado y activo, de cualquier rol."""

    @wraps(funcion)
    def envoltura(*args, **kwargs):
        _cargar_usuario_autenticado()
        return funcion(*args, **kwargs)

    return envoltura


def requiere_rol(*roles):
    """Exige un usuario autenticado cuyo rol esté en `roles` (o administrador)."""
    if not roles:
        raise ValueError("requiere_rol necesita al menos un rol; use requiere_autenticacion.")

    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            usuario = _cargar_usuario_autenticado()
            if not tiene_rol(usuario, roles):
                raise AccesoDenegadoError(MENSAJE_ACCESO_DENEGADO)
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def usuario_actual():
    """Usuario autenticado de la petición (solo dentro de rutas protegidas)."""
    return g.usuario


def exigir_propietario(id_usuario_propietario, permitir_administrador=True, mensaje=None):
    """Para recursos de un cliente (direcciones, carrito, pedidos).

    Si el recurso no pertenece al usuario autenticado responde 404, no 403,
    para no revelar que existe. El administrador puede acceder si
    permitir_administrador es True.

    Uso previsto en los servicios/controladores de las próximas etapas:
        direccion = DireccionDAO.obtener(conn, id_direccion)
        if direccion is None: raise RecursoNoEncontradoError(...)
        exigir_propietario(direccion.id_usuario)
    Para listados, filtrar directamente en SQL con WHERE id_usuario = %s usando
    usuario_actual().id_usuario (nunca un id recibido del cliente).
    """
    usuario = usuario_actual()
    if usuario.id_usuario == id_usuario_propietario:
        return
    if permitir_administrador and usuario.es_administrador:
        return
    raise RecursoNoEncontradoError(mensaje or "El recurso solicitado no existe.")
