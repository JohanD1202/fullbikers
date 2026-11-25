"""Pruebas unitarias de RF-10 (PATCH /api/perfil) con la tabla usuario en memoria."""
import pytest

from models.usuario import ADMINISTRADOR, CLIENTE, EMPLEADO
from tests.conftest import cabecera_bearer, crear_token


@pytest.fixture
def sesion(app, repositorio):
    """Cliente registrado en el repositorio falso y su cabecera Authorization."""
    usuario = repositorio.agregar("ana@ejemplo.com", rol=CLIENTE)
    return usuario, cabecera_bearer(crear_token(app, usuario.id_usuario))


def _patch(client, cabecera, cuerpo):
    return client.patch("/api/perfil", json=cuerpo, headers=cabecera)


def test_actualiza_y_normaliza_campos(client, sesion):
    usuario, cabecera = sesion
    respuesta = _patch(client, cabecera, {"nombre": "  Ana María ", "correo": " ANA.M@Ejemplo.com ",
                                          "telefono": "300 123 4567"})
    assert respuesta.status_code == 200
    assert respuesta.get_json()["usuario"] == {
        "id_usuario": usuario.id_usuario, "nombre": "Ana María", "apellido": "Apellido",
        "correo": "ana.m@ejemplo.com", "telefono": "300 123 4567", "rol": "cliente",
    }
    # La consulta (RF-10) reutiliza /api/auth/me y refleja el cambio.
    assert client.get("/api/auth/me", headers=cabecera).get_json()["usuario"]["nombre"] == "Ana María"


def test_actualizacion_parcial_no_toca_otros_campos(client, sesion):
    usuario, cabecera = sesion
    _patch(client, cabecera, {"apellido": "Gómez"})
    assert (usuario.nombre, usuario.apellido, usuario.correo) == ("Nombre", "Gómez", "ana@ejemplo.com")


def test_telefono_vacio_o_null_lo_elimina(client, sesion):
    usuario, cabecera = sesion
    usuario.telefono = "3001234567"
    assert _patch(client, cabecera, {"telefono": None}).get_json()["usuario"]["telefono"] is None


def test_respuesta_sin_datos_sensibles(client, sesion):
    texto = _patch(client, sesion[1], {"nombre": "Ana"}).get_data(as_text=True)
    assert "contrasena" not in texto and "scrypt" not in texto and "activo" not in texto


@pytest.mark.parametrize("campo", ["rol", "activo", "id_usuario", "contrasena", "contrasena_hash", "fecha_registro"])
def test_campos_administrativos_no_permitidos(client, sesion, campo):
    usuario, cabecera = sesion
    respuesta = _patch(client, cabecera, {"nombre": "Ana", campo: ADMINISTRADOR})
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["codigo"] == "campo_no_permitido"
    assert (usuario.rol, usuario.nombre) == (CLIENTE, "Nombre")


@pytest.mark.parametrize(
    "cuerpo, campo",
    [
        ({"nombre": "  "}, "nombre"),
        ({"apellido": None}, "apellido"),
        ({"nombre": "x" * 81}, "nombre"),
        ({"correo": "no-es-correo"}, "correo"),
        ({"correo": ""}, "correo"),
        ({"telefono": "abc"}, "telefono"),
        ({}, "_"),
    ],
)
def test_campos_invalidos(client, sesion, cuerpo, campo):
    respuesta = _patch(client, sesion[1], cuerpo)
    assert respuesta.status_code == 400
    assert campo in respuesta.get_json()["error"]["detalles"]["campos"]


def test_cuerpo_no_json(client, sesion):
    respuesta = client.patch("/api/perfil", data="texto", content_type="application/json", headers=sesion[1])
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["codigo"] == "solicitud_invalida"


def test_correo_duplicado_409(client, sesion, repositorio):
    repositorio.agregar("ocupado@ejemplo.com")
    respuesta = _patch(client, sesion[1], {"correo": "OCUPADO@ejemplo.com"})
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["codigo"] == "correo_ya_registrado"
    assert sesion[0].correo == "ana@ejemplo.com"


def test_mismo_correo_propio_no_es_duplicado(client, sesion):
    assert _patch(client, sesion[1], {"correo": "Ana@Ejemplo.com"}).status_code == 200


def test_sin_autenticacion_401(client, repositorio):
    assert client.patch("/api/perfil", json={"nombre": "Ana"}).status_code == 401


@pytest.mark.parametrize("rol, esperado", [(EMPLEADO, 403), (ADMINISTRADOR, 200)])
def test_roles(app, client, repositorio, rol, esperado):
    usuario = repositorio.agregar("x@ejemplo.com", rol=rol)
    respuesta = _patch(client, cabecera_bearer(crear_token(app, usuario.id_usuario, rol)), {"nombre": "Otro"})
    assert respuesta.status_code == esperado
