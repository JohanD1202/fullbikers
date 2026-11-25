"""Configuración de logging con ocultamiento de credenciales."""
import logging
import re

_PATRONES_SENSIBLES = (
    # postgresql://usuario:contraseña@host -> postgresql://usuario:***@host
    (re.compile(r"(postgres(?:ql)?://[^:/\s@]+:)[^@\s]+@", re.IGNORECASE), r"\1***@"),
    # password=... en cadenas clave=valor de libpq
    (re.compile(r"(password\s*=\s*)\S+", re.IGNORECASE), r"\1***"),
    # Authorization: Bearer <token>
    (re.compile(r"(bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE), r"\1***"),
)


def ocultar_datos_sensibles(texto):
    for patron, reemplazo in _PATRONES_SENSIBLES:
        texto = patron.sub(reemplazo, texto)
    return texto


class FormateadorSeguro(logging.Formatter):
    """Aplica ocultar_datos_sensibles a la línea completa, incluidas las trazas."""

    def format(self, record):
        return ocultar_datos_sensibles(super().format(record))


def configurar_logging(nivel):
    raiz = logging.getLogger()
    if not any(isinstance(h.formatter, FormateadorSeguro) for h in raiz.handlers):
        manejador = logging.StreamHandler()
        manejador.setFormatter(FormateadorSeguro("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        raiz.addHandler(manejador)
    raiz.setLevel(getattr(logging, nivel, logging.INFO))
