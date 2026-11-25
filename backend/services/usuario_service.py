"""Casos de uso de usuarios: validación, creación y consulta.

Lo usan el registro público (solo clientes), los comandos de consola
(administrador inicial y usuarios de prueba) y el middleware de autenticación.
"""
import re

from psycopg import errors
from werkzeug.security import generate_password_hash

from config import database
from dao.usuario_dao import UsuarioDAO
from exceptions import ConflictoError, ValidacionError
from models.usuario import ROLES

# Mismas reglas que los CHECK de la tabla usuario (database/schema.sql).
_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PATRON_TELEFONO = re.compile(r"^\+?[0-9][0-9 ()-]{5,18}[0-9]$")
_LONGITUD_NOMBRE = 80
_LONGITUD_CORREO = 254
CONTRASENA_MIN = 8
CONTRASENA_MAX = 128

MENSAJE_CORREO_DUPLICADO = "Ya existe una cuenta registrada con ese correo electrónico."


def normalizar_correo(correo):
    return correo.strip().lower() if isinstance(correo, str) else ""


def _texto_obligatorio(datos, campo, etiqueta, errores):
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        errores[campo] = f"{etiqueta} es obligatorio."
        return None
    valor = valor.strip()
    if len(valor) > _LONGITUD_NOMBRE:
        errores[campo] = f"{etiqueta} admite como máximo {_LONGITUD_NOMBRE} caracteres."
    return valor


def validar_contrasena(contrasena):
    """Devuelve el mensaje de error o None si la contraseña es aceptable."""
    if not isinstance(contrasena, str) or not contrasena:
        return "La contraseña es obligatoria."
    if not CONTRASENA_MIN <= len(contrasena) <= CONTRASENA_MAX:
        return f"La contraseña debe tener entre {CONTRASENA_MIN} y {CONTRASENA_MAX} caracteres."
    if not any(c.isalpha() for c in contrasena) or not any(c.isdigit() for c in contrasena):
        return "La contraseña debe incluir al menos una letra y un número."
    return None


def validar_datos_usuario(datos):
    """Valida y normaliza nombre, apellido, correo, teléfono y contraseña.

    Devuelve un diccionario limpio o lanza ValidacionError con todos los
    errores por campo en detalles["campos"].
    """
    errores = {}
    nombre = _texto_obligatorio(datos, "nombre", "El nombre", errores)
    apellido = _texto_obligatorio(datos, "apellido", "El apellido", errores)

    correo = normalizar_correo(datos.get("correo"))
    if not correo:
        errores["correo"] = "El correo electrónico es obligatorio."
    elif len(correo) > _LONGITUD_CORREO or not _PATRON_CORREO.match(correo):
        errores["correo"] = "El correo electrónico no tiene un formato válido."

    telefono = datos.get("telefono")
    if telefono is None or (isinstance(telefono, str) and not telefono.strip()):
        telefono = None
    elif not isinstance(telefono, str) or not _PATRON_TELEFONO.match(telefono.strip()):
        errores["telefono"] = "El teléfono solo admite números, espacios, guiones, paréntesis y un + inicial (7 a 20 caracteres)."
    else:
        telefono = telefono.strip()

    # La contraseña nunca se recorta ni se registra.
    problema = validar_contrasena(datos.get("contrasena"))
    if problema:
        errores["contrasena"] = problema

    if errores:
        raise ValidacionError("Revise los datos ingresados.", detalles={"campos": errores})
    return {
        "nombre": nombre,
        "apellido": apellido,
        "correo": correo,
        "telefono": telefono,
        "contrasena": datos["contrasena"],
    }


def crear_usuario(datos, rol):
    """Valida los datos, genera el hash y crea un usuario activo con el rol dado.

    El rol lo decide siempre el código que llama (registro público = cliente),
    nunca los datos recibidos. Un correo existente produce ConflictoError: no
    se modifica ni se promueve ningún usuario existente.
    """
    if rol not in ROLES:
        raise ValueError(f"Rol desconocido: {rol!r}")
    limpios = validar_datos_usuario(datos)
    contrasena_hash = generate_password_hash(limpios["contrasena"])  # scrypt (Werkzeug)

    try:
        with database.transaccion() as conn:
            if UsuarioDAO.obtener_por_correo(conn, limpios["correo"]) is not None:
                raise ConflictoError(MENSAJE_CORREO_DUPLICADO, codigo="correo_ya_registrado")
            return UsuarioDAO.crear(
                conn,
                nombre=limpios["nombre"],
                apellido=limpios["apellido"],
                correo=limpios["correo"],
                contrasena_hash=contrasena_hash,
                telefono=limpios["telefono"],
                rol=rol,
            )
    except errors.UniqueViolation as exc:
        # Dos registros simultáneos con el mismo correo: lo resuelve la
        # restricción uq_usuario_correo de PostgreSQL.
        raise ConflictoError(MENSAJE_CORREO_DUPLICADO, codigo="correo_ya_registrado") from exc
    except errors.CheckViolation as exc:
        raise ValidacionError("Revise los datos ingresados.") from exc


def obtener_por_correo(correo):
    with database.obtener_conexion() as conn:
        return UsuarioDAO.obtener_por_correo(conn, normalizar_correo(correo))


def obtener_usuario_activo(id_usuario):
    """Usuario con su rol vigente si existe y está activo; si no, None."""
    with database.obtener_conexion() as conn:
        usuario = UsuarioDAO.obtener_por_id(conn, id_usuario)
    if usuario is None or not usuario.activo:
        return None
    return usuario
