"""Casos de uso de autenticación: registro de clientes e inicio de sesión.

Decisiones (ver backend/README.md §8):
  * El registro público crea SIEMPRE un cliente; el rol no se recibe del usuario.
  * JWT de 60 minutos sin refresh token. El token identifica al usuario
    (sub = id_usuario); el rol y el estado se leen de PostgreSQL en cada
    petición protegida (middleware/auth.py), no se confía en el token.
  * Mensaje único para correo inexistente, contraseña incorrecta o cuenta
    inactiva (no revela qué correos existen).
  * Nunca se registran contraseñas ni tokens en los logs.
"""
import logging

from flask import current_app
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from exceptions import ApiError, DemasiadosIntentosError, ValidacionError
from models.usuario import CLIENTE
from services import usuario_service
from services.limitador_intentos import LimitadorIntentos

logger = logging.getLogger(__name__)

CAMPOS_REGISTRO = frozenset({"nombre", "apellido", "correo", "contrasena", "telefono"})
_EXTENSION_LIMITADOR = "fullbikers_limitador_login"
_MENSAJE_CREDENCIALES = "Correo electrónico o contraseña incorrectos."

# Hash de referencia para igualar el tiempo de respuesta cuando el correo no
# existe (se calcula una sola vez, de forma diferida).
_hash_ficticio = None


def init_app(app):
    app.extensions[_EXTENSION_LIMITADOR] = LimitadorIntentos()


def _limitador():
    return current_app.extensions[_EXTENSION_LIMITADOR]


def _verificar_contra_hash_ficticio(contrasena):
    global _hash_ficticio
    if _hash_ficticio is None:
        _hash_ficticio = generate_password_hash("contrasena-ficticia-sin-uso-0")
    check_password_hash(_hash_ficticio, contrasena)


def registrar_cliente(datos):
    """Crea una cuenta de cliente. Rechaza cualquier campo fuera de la lista blanca."""
    if not isinstance(datos, dict):
        raise ApiError("El cuerpo de la solicitud debe ser un objeto JSON.", codigo="solicitud_invalida")
    no_permitidos = sorted(set(datos) - CAMPOS_REGISTRO)
    if no_permitidos:
        raise ApiError(
            "La solicitud incluye campos no permitidos.",
            codigo="campo_no_permitido",
            detalles={"campos": no_permitidos},
        )
    usuario = usuario_service.crear_usuario(datos, rol=CLIENTE)
    logger.info("Cliente registrado (id_usuario=%s).", usuario.id_usuario)
    return usuario


def iniciar_sesion(datos, ip):
    """Verifica las credenciales y devuelve (access_token, usuario)."""
    if not isinstance(datos, dict):
        raise ApiError("El cuerpo de la solicitud debe ser un objeto JSON.", codigo="solicitud_invalida")
    correo = usuario_service.normalizar_correo(datos.get("correo"))
    contrasena = datos.get("contrasena")
    errores = {}
    if not correo:
        errores["correo"] = "El correo electrónico es obligatorio."
    if not isinstance(contrasena, str) or not contrasena:
        errores["contrasena"] = "La contraseña es obligatoria."
    if errores:
        raise ValidacionError("Revise los datos ingresados.", detalles={"campos": errores})

    clave = (correo, ip or "-")
    espera = _limitador().segundos_bloqueo(clave)
    if espera:
        logger.warning("Inicio de sesión bloqueado temporalmente por intentos fallidos.")
        raise DemasiadosIntentosError(
            "Demasiados intentos fallidos. Intente de nuevo más tarde.",
            segundos_espera=espera,
        )

    usuario = usuario_service.obtener_por_correo(correo)
    if len(contrasena) > usuario_service.CONTRASENA_MAX:
        # Ninguna contraseña registrada supera el máximo; no se calcula el hash.
        valido = False
    elif usuario is None:
        _verificar_contra_hash_ficticio(contrasena)
        valido = False
    else:
        valido = check_password_hash(usuario.contrasena_hash, contrasena) and usuario.activo

    if not valido:
        _limitador().registrar_fallo(clave)
        logger.info("Inicio de sesión fallido.")
        raise ApiError(_MENSAJE_CREDENCIALES, codigo="credenciales_invalidas", status_code=401)

    _limitador().reiniciar(clave)
    token = create_access_token(identity=str(usuario.id_usuario), additional_claims={"rol": usuario.rol})
    logger.info("Inicio de sesión correcto (id_usuario=%s, rol=%s).", usuario.id_usuario, usuario.rol)
    return token, usuario
