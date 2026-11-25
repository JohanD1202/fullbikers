"""Excepciones de la aplicación.

Los controladores y servicios lanzan estas excepciones; el manejador
centralizado (middleware/error_handlers.py) las convierte en respuestas JSON
con el formato {"error": {"codigo": ..., "mensaje": ...}}.
"""


class ApiError(Exception):
    """Error controlado que se devuelve al cliente tal cual."""

    status_code = 400
    codigo = "solicitud_invalida"

    def __init__(self, mensaje, codigo=None, status_code=None, detalles=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        if codigo is not None:
            self.codigo = codigo
        if status_code is not None:
            self.status_code = status_code
        # Información adicional segura para el cliente (por ejemplo, el campo inválido).
        self.detalles = detalles


class ParametroInvalidoError(ApiError):
    status_code = 400
    codigo = "parametro_invalido"


class RecursoNoEncontradoError(ApiError):
    status_code = 404
    codigo = "recurso_no_encontrado"


class BaseDeDatosNoDisponibleError(Exception):
    """PostgreSQL no está configurado o no responde. Se traduce a HTTP 503."""
