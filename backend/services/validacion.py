"""Validación común de cuerpos JSON para los servicios.

Todas las funciones acumulan errores por campo en el diccionario `errores`;
el servicio lanza ValidacionError (400 "validacion") si queda alguno, de modo
que el frontend recibe todos los problemas en una sola respuesta.
"""
from exceptions import ApiError, ValidacionError

ENTERO_MAXIMO_POSTGRES = 2_147_483_647


def exigir_objeto(datos):
    if not isinstance(datos, dict):
        raise ApiError("El cuerpo de la solicitud debe ser un objeto JSON.", codigo="solicitud_invalida")


def rechazar_campos_no_permitidos(datos, permitidos):
    """400 campo_no_permitido si el cuerpo trae campos fuera de la lista blanca."""
    no_permitidos = sorted(set(datos) - set(permitidos))
    if no_permitidos:
        raise ApiError(
            "La solicitud incluye campos no permitidos.",
            codigo="campo_no_permitido",
            detalles={"campos": no_permitidos},
        )


def exigir_algun_campo(datos, permitidos):
    if not set(datos) & set(permitidos):
        raise ValidacionError(
            "Debe enviar al menos un campo para actualizar.",
            detalles={"campos": {"_": f"Campos admitidos: {', '.join(sorted(permitidos))}."}},
        )


def lanzar_si_hay_errores(errores):
    if errores:
        raise ValidacionError("Revise los datos ingresados.", detalles={"campos": errores})


def entero_positivo(datos, campo, etiqueta, errores, maximo=ENTERO_MAXIMO_POSTGRES):
    """Entero JSON >= 1 (no se aceptan cadenas, decimales ni booleanos)."""
    valor = datos.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= maximo:
        errores[campo] = f"{etiqueta} debe ser un número entero entre 1 y {maximo}."
        return None
    return valor


def texto(datos, campo, etiqueta, errores, longitud_maxima, obligatorio=True):
    """Texto sin espacios extremos. Opcional: None, ausente o vacío -> None."""
    valor = datos.get(campo)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            errores[campo] = f"{etiqueta} es obligatorio."
        return None
    if not isinstance(valor, str):
        errores[campo] = f"{etiqueta} debe ser un texto."
        return None
    valor = valor.strip()
    if len(valor) > longitud_maxima:
        errores[campo] = f"{etiqueta} admite como máximo {longitud_maxima} caracteres."
        return None
    return valor


def booleano(datos, campo, etiqueta, errores):
    valor = datos.get(campo)
    if not isinstance(valor, bool):
        errores[campo] = f"{etiqueta} debe ser true o false."
        return None
    return valor
