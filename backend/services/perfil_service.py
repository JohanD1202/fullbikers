"""RF-10: consultar y actualizar los datos personales del usuario autenticado.

La consulta reutiliza GET /api/auth/me. La actualización solo admite nombre,
apellido, correo y teléfono: rol, estado, identificador y contraseña no se
modifican aquí (rol y estado corresponden a la administración de usuarios).
"""
import logging

from psycopg import errors

from config import database
from dao.usuario_dao import UsuarioDAO
from exceptions import ConflictoError, NoAutenticadoError, ValidacionError
from services import usuario_service, validacion

logger = logging.getLogger(__name__)

CAMPOS_PERFIL = frozenset({"nombre", "apellido", "correo", "telefono"})


def actualizar_perfil(id_usuario, datos):
    """Actualiza los campos enviados y devuelve el usuario actualizado."""
    validacion.exigir_objeto(datos)
    validacion.rechazar_campos_no_permitidos(datos, CAMPOS_PERFIL)
    validacion.exigir_algun_campo(datos, CAMPOS_PERFIL)
    cambios = usuario_service.validar_datos_perfil(datos)

    try:
        with database.transaccion() as conn:
            if "correo" in cambios and UsuarioDAO.existe_correo_de_otro(conn, cambios["correo"], id_usuario):
                raise ConflictoError(usuario_service.MENSAJE_CORREO_DUPLICADO, codigo="correo_ya_registrado")
            usuario = UsuarioDAO.actualizar_datos_personales(conn, id_usuario, cambios)
    except errors.UniqueViolation as exc:
        raise ConflictoError(usuario_service.MENSAJE_CORREO_DUPLICADO, codigo="correo_ya_registrado") from exc
    except errors.CheckViolation as exc:
        raise ValidacionError("Revise los datos ingresados.") from exc

    if usuario is None:
        # Desactivado entre la autenticación y la actualización.
        raise NoAutenticadoError("Debe iniciar sesión para continuar.")
    logger.info("Perfil actualizado (id_usuario=%s, campos=%s).", id_usuario, sorted(cambios))
    return usuario
