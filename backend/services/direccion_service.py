"""RF-11: registrar, consultar, editar, seleccionar (principal) y desactivar
direcciones de entrega del usuario autenticado.

Reglas:
  * El propietario es siempre el usuario del token; el cuerpo no puede
    indicar id_usuario (lista blanca de campos).
  * Una dirección ajena, inexistente o inactiva responde 404.
  * Como máximo una dirección principal activa (índice ux_direccion_principal_activa):
    se desmarca la anterior antes de marcar la nueva, en la misma transacción.
  * La primera dirección activa del usuario queda como principal.
  * Eliminar = activo = false (y principal = false). Nunca DELETE.
  * Los pedidos guardan una copia de la dirección, por lo que editar o
    desactivar una dirección no altera pedidos anteriores.
"""
import re

from config import database
from dao.direccion_dao import DireccionDAO
from exceptions import RecursoNoEncontradoError
from services import validacion

CAMPOS = frozenset({"departamento", "municipio", "direccion", "complemento", "codigo_postal", "principal"})
_PATRON_CODIGO_POSTAL = re.compile(r"^[0-9]{4,10}$")
_MENSAJE_NO_ENCONTRADA = "La dirección solicitada no existe."


def _no_encontrada():
    return RecursoNoEncontradoError(_MENSAJE_NO_ENCONTRADA, codigo="direccion_no_encontrada")


def _validar(datos, parcial):
    """Valida los campos presentes (o todos los obligatorios si no es parcial)."""
    errores = {}
    limpios = {}
    reglas = (
        ("departamento", "El departamento", 60, True),
        ("municipio", "El municipio", 80, True),
        ("direccion", "La dirección", 150, True),
        ("complemento", "El complemento", 100, False),
    )
    for campo, etiqueta, maximo, obligatorio in reglas:
        if not parcial or campo in datos:
            limpios[campo] = validacion.texto(datos, campo, etiqueta, errores, maximo, obligatorio)

    if not parcial or "codigo_postal" in datos:
        codigo = validacion.texto(datos, "codigo_postal", "El código postal", errores, 10, obligatorio=False)
        if codigo is not None and not _PATRON_CODIGO_POSTAL.match(codigo):
            errores["codigo_postal"] = "El código postal debe tener entre 4 y 10 dígitos."
        limpios["codigo_postal"] = codigo

    if "principal" in datos:
        limpios["principal"] = validacion.booleano(datos, "principal", "El campo principal", errores)

    validacion.lanzar_si_hay_errores(errores)
    return limpios


def listar(id_usuario):
    with database.obtener_conexion() as conn:
        return DireccionDAO.listar_activas(conn, id_usuario)


def obtener(id_usuario, id_direccion):
    with database.obtener_conexion() as conn:
        direccion = DireccionDAO.obtener_activa(conn, id_direccion, id_usuario)
    if direccion is None:
        raise _no_encontrada()
    return direccion


def crear(id_usuario, datos):
    validacion.exigir_objeto(datos)
    validacion.rechazar_campos_no_permitidos(datos, CAMPOS)
    limpios = _validar(datos, parcial=False)

    with database.transaccion() as conn:
        DireccionDAO.bloquear_usuario(conn, id_usuario)
        if DireccionDAO.contar_activas(conn, id_usuario) == 0:
            limpios["principal"] = True
        if limpios.get("principal"):
            DireccionDAO.desmarcar_principal(conn, id_usuario)
        return DireccionDAO.crear(conn, id_usuario, limpios)


def actualizar(id_usuario, id_direccion, datos):
    validacion.exigir_objeto(datos)
    validacion.rechazar_campos_no_permitidos(datos, CAMPOS)
    validacion.exigir_algun_campo(datos, CAMPOS)
    cambios = _validar(datos, parcial=True)

    with database.transaccion() as conn:
        DireccionDAO.bloquear_usuario(conn, id_usuario)
        if DireccionDAO.obtener_activa(conn, id_direccion, id_usuario) is None:
            raise _no_encontrada()
        if cambios.get("principal"):
            DireccionDAO.desmarcar_principal(conn, id_usuario)
        return DireccionDAO.actualizar(conn, id_direccion, id_usuario, cambios)


def eliminar(id_usuario, id_direccion):
    with database.transaccion() as conn:
        DireccionDAO.bloquear_usuario(conn, id_usuario)
        if not DireccionDAO.desactivar(conn, id_direccion, id_usuario):
            raise _no_encontrada()
