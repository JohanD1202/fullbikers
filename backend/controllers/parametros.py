"""Validación de parámetros de consulta (query string) para los controladores."""
from flask import request

from exceptions import ParametroInvalidoError

# Límite defensivo para identificadores INTEGER de PostgreSQL.
_ENTERO_MAXIMO_POSTGRES = 2_147_483_647


def entero_positivo(nombre, predeterminado=None, maximo=_ENTERO_MAXIMO_POSTGRES):
    """Lee un entero >= 1 del query string. Ausente o vacío -> predeterminado."""
    valor = request.args.get(nombre, "").strip()
    if not valor:
        return predeterminado
    if not valor.isdigit() or not 1 <= int(valor) <= maximo:
        raise ParametroInvalidoError(
            f"El parámetro '{nombre}' debe ser un número entero entre 1 y {maximo}.",
            detalles={"parametro": nombre},
        )
    return int(valor)


def texto_opcional(nombre, longitud_maxima):
    """Lee un texto del query string sin espacios extremos. Vacío -> None."""
    valor = request.args.get(nombre, "").strip()
    if not valor:
        return None
    if len(valor) > longitud_maxima:
        raise ParametroInvalidoError(
            f"El parámetro '{nombre}' admite como máximo {longitud_maxima} caracteres.",
            detalles={"parametro": nombre},
        )
    return valor
