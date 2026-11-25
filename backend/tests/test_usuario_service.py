import pytest
from psycopg import errors

from dao.usuario_dao import UsuarioDAO
from exceptions import ConflictoError, ValidacionError
from models.usuario import CLIENTE, EMPLEADO, Usuario
from services import usuario_service
from services.limitador_intentos import LimitadorIntentos
from tests.conftest import ConexionFalsa

DATOS = {"nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "contrasena": "Clave2026"}


@pytest.mark.parametrize("telefono", ["3001234567", "+57 300 123 4567", "602 (224) 55-66", None, "", "  "])
def test_telefonos_validos(telefono):
    assert usuario_service.validar_datos_usuario({**DATOS, "telefono": telefono})


@pytest.mark.parametrize("telefono", ["12345", "(602) 224-5566", "300-ABC-4567", "+", "1" * 21])
def test_telefonos_invalidos(telefono):
    with pytest.raises(ValidacionError) as error:
        usuario_service.validar_datos_usuario({**DATOS, "telefono": telefono})
    assert "telefono" in error.value.detalles["campos"]


def test_validacion_reporta_todos_los_campos():
    with pytest.raises(ValidacionError) as error:
        usuario_service.validar_datos_usuario({})
    assert set(error.value.detalles["campos"]) == {"nombre", "apellido", "correo", "contrasena"}


def test_contrasena_no_se_recorta():
    assert usuario_service.validar_datos_usuario({**DATOS, "contrasena": " Clave2026 "})["contrasena"] == " Clave2026 "


def test_crear_usuario_rol_desconocido():
    with pytest.raises(ValueError):
        usuario_service.crear_usuario(DATOS, rol="visitante")


def test_crear_usuario_traduce_violacion_de_unicidad(repositorio, monkeypatch):
    def crear_con_carrera(*_args, **_kwargs):
        raise errors.UniqueViolation("duplicate key value violates unique constraint")

    monkeypatch.setattr(UsuarioDAO, "crear", staticmethod(crear_con_carrera))
    with pytest.raises(ConflictoError) as error:
        usuario_service.crear_usuario(DATOS, rol=CLIENTE)
    assert error.value.codigo == "correo_ya_registrado"


def test_obtener_usuario_activo_ignora_inactivos(repositorio):
    activo = repositorio.agregar("a@ejemplo.com", rol=EMPLEADO)
    inactivo = repositorio.agregar("b@ejemplo.com", activo=False)
    assert usuario_service.obtener_usuario_activo(activo.id_usuario).rol == EMPLEADO
    assert usuario_service.obtener_usuario_activo(inactivo.id_usuario) is None
    assert usuario_service.obtener_usuario_activo(999) is None


def test_usuario_to_dict_y_repr_sin_hash():
    usuario = Usuario(1, "Ana", "Pérez", "ana@ejemplo.com", CLIENTE, contrasena_hash="scrypt:secreto")
    assert "contrasena_hash" not in usuario.to_dict()
    assert "scrypt" not in repr(usuario)


def test_usuario_dao_consultas_parametrizadas():
    fila = {"id_usuario": 4, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com",
            "contrasena_hash": "h" * 30, "telefono": None, "rol": "cliente", "activo": True,
            "fecha_registro": None}
    conexion = ConexionFalsa([[fila], [fila]])
    usuario = UsuarioDAO.crear(conexion, "Ana", "Pérez", "ana@ejemplo.com", "h" * 30, None, "cliente")
    assert usuario.id_usuario == 4
    consulta, parametros = conexion.ejecutadas[0]
    assert "INSERT INTO usuario" in consulta and "RETURNING" in consulta
    assert "id_usuario" not in consulta.split("VALUES")[0].split("(")[1]  # identidad: la genera PostgreSQL
    assert parametros == ("Ana", "Pérez", "ana@ejemplo.com", "h" * 30, None, "cliente")

    UsuarioDAO.obtener_por_correo(conexion, "x@y.com' OR '1'='1")
    consulta, parametros = conexion.ejecutadas[1]
    assert "%s" in consulta and "OR '1'" not in consulta
    assert parametros == ("x@y.com' OR '1'='1",)


class RelojFalso:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora


def test_limitador_ventana_deslizante():
    reloj = RelojFalso()
    limitador = LimitadorIntentos(max_intentos=3, ventana_segundos=60, reloj=reloj)
    clave = ("ana@ejemplo.com", "127.0.0.1")
    for _ in range(3):
        assert limitador.segundos_bloqueo(clave) == 0
        limitador.registrar_fallo(clave)
        reloj.ahora += 10
    assert limitador.segundos_bloqueo(clave) > 0
    reloj.ahora += 31  # el primer fallo sale de la ventana
    assert limitador.segundos_bloqueo(clave) == 0


def test_limitador_reiniciar():
    limitador = LimitadorIntentos(max_intentos=1, ventana_segundos=60)
    limitador.registrar_fallo("k")
    assert limitador.segundos_bloqueo("k") > 0
    limitador.reiniciar("k")
    assert limitador.segundos_bloqueo("k") == 0
