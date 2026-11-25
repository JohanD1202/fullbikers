"""Manejo centralizado de errores: toda respuesta de error es JSON.

Formato:  {"error": {"codigo": "<identificador>", "mensaje": "<texto para el usuario>"}}
Opcional: "detalles" con información segura (p. ej., el parámetro inválido).

Nunca se devuelven trazas, consultas SQL, nombres de servidores ni mensajes
internos de PostgreSQL (RNF18). El detalle técnico va solo al log.
"""
import logging

import psycopg
from flask import jsonify
from psycopg_pool import PoolTimeout
from werkzeug.exceptions import HTTPException

from exceptions import ApiError, BaseDeDatosNoDisponibleError

logger = logging.getLogger(__name__)

_ERRORES_HTTP = {
    400: ("solicitud_invalida", "La solicitud no es válida."),
    401: ("no_autenticado", "Debe iniciar sesión para continuar."),
    403: ("acceso_denegado", "No tiene permisos para realizar esta acción."),
    404: ("recurso_no_encontrado", "El recurso solicitado no existe."),
    405: ("metodo_no_permitido", "Método HTTP no permitido para este recurso."),
    413: ("solicitud_demasiado_grande", "La solicitud supera el tamaño permitido."),
    415: ("tipo_de_contenido_no_soportado", "Tipo de contenido no soportado."),
    429: ("demasiadas_solicitudes", "Demasiadas solicitudes. Intente más tarde."),
}

_MENSAJE_BD_NO_DISPONIBLE = "El servicio de datos no está disponible en este momento. Intente más tarde."
_MENSAJE_ERROR_INTERNO = "Ocurrió un error inesperado. Intente más tarde."


def respuesta_error(codigo, mensaje, status_code, detalles=None):
    error = {"codigo": codigo, "mensaje": mensaje}
    if detalles:
        error["detalles"] = detalles
    return jsonify({"error": error}), status_code


def registrar_manejadores(app):
    @app.errorhandler(ApiError)
    def _api_error(exc):
        respuesta, status_code = respuesta_error(exc.codigo, exc.mensaje, exc.status_code, exc.detalles)
        segundos_espera = getattr(exc, "segundos_espera", None)
        if segundos_espera:
            respuesta.headers["Retry-After"] = str(segundos_espera)
        return respuesta, status_code

    @app.errorhandler(HTTPException)
    def _http_error(exc):
        codigo, mensaje = _ERRORES_HTTP.get(exc.code, ("error_http", "La solicitud no pudo procesarse."))
        return respuesta_error(codigo, mensaje, exc.code)

    @app.errorhandler(BaseDeDatosNoDisponibleError)
    def _bd_no_disponible(exc):
        causa = type(exc.__cause__).__name__ if exc.__cause__ else "-"
        logger.warning("Base de datos no disponible: %s (causa: %s)", exc, causa)
        return respuesta_error("base_de_datos_no_disponible", _MENSAJE_BD_NO_DISPONIBLE, 503)

    @app.errorhandler(PoolTimeout)
    @app.errorhandler(psycopg.OperationalError)
    def _bd_operacional(exc):
        # El mensaje de libpq puede incluir el host: solo se registra la clase.
        logger.warning("Fallo de conexión con PostgreSQL: %s", type(exc).__name__)
        return respuesta_error("base_de_datos_no_disponible", _MENSAJE_BD_NO_DISPONIBLE, 503)

    @app.errorhandler(psycopg.Error)
    def _bd_error(exc):
        diag = getattr(exc, "diag", None)
        logger.error(
            "Error de PostgreSQL %s (SQLSTATE %s): %s",
            type(exc).__name__,
            getattr(exc, "sqlstate", None),
            getattr(diag, "message_primary", None),
        )
        return respuesta_error("error_interno", _MENSAJE_ERROR_INTERNO, 500)

    @app.errorhandler(Exception)
    def _error_no_controlado(exc):
        logger.exception("Error no controlado")
        return respuesta_error("error_interno", _MENSAJE_ERROR_INTERNO, 500)
