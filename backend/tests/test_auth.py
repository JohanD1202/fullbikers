"""Pruebas unitarias de /api/auth/* y del middleware de autorización.

La tabla usuario se sustituye por RepositorioUsuariosFalso (tests/conftest.py);
el hash (Werkzeug) y los JWT (Flask-JWT-Extended) son reales.
"""
import logging
from datetime import timedelta

import jwt as pyjwt
import pytest
from flask import jsonify

from middleware.auth import exigir_propietario, requiere_rol
from models.usuario import ADMINISTRADOR, CLIENTE, EMPLEADO
from tests.conftest import cabecera_bearer, crear_token

REGISTRO_VALIDO = {
    "nombre": "  Ana ",
    "apellido": "Pérez",
    "correo": "  Ana.Perez@Ejemplo.COM ",
    "contrasena": "Segura2026",
    "telefono": "+57 300 000 0000",
}


def _error(respuesta):
    return respuesta.get_json()["error"]


def _login(client, correo, contrasena):
    return client.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

def test_registro_exitoso_crea_cliente_normalizado(client, repositorio):
    respuesta = client.post("/api/auth/register", json=REGISTRO_VALIDO)
    assert respuesta.status_code == 201
    usuario = respuesta.get_json()["usuario"]
    assert usuario == {
        "id_usuario": 1, "nombre": "Ana", "apellido": "Pérez",
        "correo": "ana.perez@ejemplo.com", "telefono": "+57 300 000 0000", "rol": "cliente",
    }
    guardado = repositorio.filas[1]
    assert guardado.rol == CLIENTE
    assert guardado.contrasena_hash.startswith("scrypt:")
    assert "Segura2026" not in guardado.contrasena_hash


def test_registro_no_devuelve_contrasena_ni_hash(client, repositorio):
    texto = client.post("/api/auth/register", json=REGISTRO_VALIDO).get_data(as_text=True)
    assert "contrasena" not in texto
    assert "scrypt" not in texto


def test_registro_telefono_opcional(client, repositorio):
    datos = {k: v for k, v in REGISTRO_VALIDO.items() if k != "telefono"}
    respuesta = client.post("/api/auth/register", json=datos)
    assert respuesta.status_code == 201
    assert respuesta.get_json()["usuario"]["telefono"] is None


def test_registro_correo_duplicado_con_otra_capitalizacion(client, repositorio):
    repositorio.agregar("ana.perez@ejemplo.com")
    respuesta = client.post("/api/auth/register", json=REGISTRO_VALIDO)
    assert respuesta.status_code == 409
    assert _error(respuesta)["codigo"] == "correo_ya_registrado"
    assert len(repositorio.filas) == 1


@pytest.mark.parametrize("campo", ["rol", "activo", "id_usuario", "contrasena_hash"])
def test_registro_rechaza_campos_no_permitidos(client, repositorio, campo):
    respuesta = client.post("/api/auth/register", json={**REGISTRO_VALIDO, campo: "administrador"})
    assert respuesta.status_code == 400
    assert _error(respuesta)["codigo"] == "campo_no_permitido"
    assert _error(respuesta)["detalles"] == {"campos": [campo]}
    assert repositorio.filas == {}


def test_intento_de_registro_como_administrador_no_crea_usuario(client, repositorio):
    respuesta = client.post("/api/auth/register", json={**REGISTRO_VALIDO, "rol": ADMINISTRADOR})
    assert respuesta.status_code == 400
    assert repositorio.filas == {}


@pytest.mark.parametrize(
    "cambios, campo",
    [
        ({"nombre": "   "}, "nombre"),
        ({"apellido": None}, "apellido"),
        ({"nombre": "x" * 81}, "nombre"),
        ({"correo": "sin-arroba.com"}, "correo"),
        ({"correo": "a@b"}, "correo"),
        ({"correo": ""}, "correo"),
        ({"contrasena": "corta1"}, "contrasena"),
        ({"contrasena": "solamenteletras"}, "contrasena"),
        ({"contrasena": "1234567890"}, "contrasena"),
        ({"contrasena": "a1" * 65}, "contrasena"),
        ({"telefono": "abc"}, "telefono"),
        ({"telefono": 3001234567}, "telefono"),
    ],
)
def test_registro_datos_invalidos(client, repositorio, cambios, campo):
    respuesta = client.post("/api/auth/register", json={**REGISTRO_VALIDO, **cambios})
    assert respuesta.status_code == 400
    assert _error(respuesta)["codigo"] == "validacion"
    assert campo in _error(respuesta)["detalles"]["campos"]
    assert repositorio.filas == {}


@pytest.mark.parametrize("cuerpo", [None, "texto", "[1, 2]"])
def test_registro_cuerpo_no_json_objeto(client, repositorio, cuerpo):
    respuesta = client.post("/api/auth/register", data=cuerpo, content_type="application/json")
    assert respuesta.status_code == 400
    assert _error(respuesta)["codigo"] == "solicitud_invalida"


# ---------------------------------------------------------------------------
# Inicio de sesión
# ---------------------------------------------------------------------------

def test_login_exitoso_devuelve_token_y_usuario(app, client, repositorio):
    repositorio.agregar("eva@ejemplo.com", "Clave2026", rol=EMPLEADO)
    respuesta = _login(client, "  EVA@ejemplo.com ", "Clave2026")
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["token_type"] == "Bearer"
    assert cuerpo["expires_in"] == 3600
    assert cuerpo["usuario"]["rol"] == "empleado"
    assert "contrasena_hash" not in cuerpo["usuario"]

    datos = pyjwt.decode(cuerpo["access_token"], app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    assert datos["sub"] == "1"
    assert datos["rol"] == "empleado"
    assert datos["exp"] - datos["iat"] == 3600


@pytest.mark.parametrize(
    "correo, contrasena",
    [("ana@ejemplo.com", "Incorrecta1"), ("nadie@ejemplo.com", "Clave2026"), ("ana@ejemplo.com", "x" * 200)],
)
def test_login_credenciales_incorrectas_mensaje_generico(client, repositorio, correo, contrasena):
    repositorio.agregar("ana@ejemplo.com", "Clave2026")
    respuesta = _login(client, correo, contrasena)
    assert respuesta.status_code == 401
    assert _error(respuesta) == {"codigo": "credenciales_invalidas",
                                 "mensaje": "Correo electrónico o contraseña incorrectos."}


def test_login_usuario_inactivo_mismo_mensaje(client, repositorio):
    repositorio.agregar("ana@ejemplo.com", "Clave2026", activo=False)
    respuesta = _login(client, "ana@ejemplo.com", "Clave2026")
    assert respuesta.status_code == 401
    assert _error(respuesta)["codigo"] == "credenciales_invalidas"


@pytest.mark.parametrize("cuerpo", [{}, {"correo": "ana@ejemplo.com"}, {"contrasena": "Clave2026"}])
def test_login_campos_obligatorios(client, repositorio, cuerpo):
    respuesta = client.post("/api/auth/login", json=cuerpo)
    assert respuesta.status_code == 400
    assert _error(respuesta)["codigo"] == "validacion"


def test_login_bloquea_tras_cinco_fallos_y_exito_reinicia(client, repositorio):
    repositorio.agregar("ana@ejemplo.com", "Clave2026")
    for _ in range(4):
        assert _login(client, "ana@ejemplo.com", "Mala12345").status_code == 401
    # Un éxito antes del quinto fallo reinicia el contador.
    assert _login(client, "ana@ejemplo.com", "Clave2026").status_code == 200
    for _ in range(5):
        assert _login(client, "ana@ejemplo.com", "Mala12345").status_code == 401
    bloqueado = _login(client, "ana@ejemplo.com", "Clave2026")
    assert bloqueado.status_code == 429
    assert _error(bloqueado)["codigo"] == "demasiadas_solicitudes"
    assert int(bloqueado.headers["Retry-After"]) > 0
    # Otro correo no se ve afectado.
    repositorio.agregar("luis@ejemplo.com", "Clave2026")
    assert _login(client, "luis@ejemplo.com", "Clave2026").status_code == 200


def test_login_no_registra_contrasena_ni_token(client, repositorio, caplog):
    repositorio.agregar("ana@ejemplo.com", "Clave2026")
    with caplog.at_level(logging.DEBUG):
        _login(client, "ana@ejemplo.com", "MalaSecreta99")
        token = _login(client, "ana@ejemplo.com", "Clave2026").get_json()["access_token"]
    assert "MalaSecreta99" not in caplog.text
    assert "Clave2026" not in caplog.text
    assert token not in caplog.text


# ---------------------------------------------------------------------------
# Usuario autenticado, cierre de sesión y validación del token
# ---------------------------------------------------------------------------

def test_me_devuelve_usuario_actual_sin_datos_sensibles(client, repositorio):
    repositorio.agregar("ana@ejemplo.com", "Clave2026")
    token = _login(client, "ana@ejemplo.com", "Clave2026").get_json()["access_token"]
    respuesta = client.get("/api/auth/me", headers=cabecera_bearer(token))
    assert respuesta.status_code == 200
    usuario = respuesta.get_json()["usuario"]
    assert usuario["correo"] == "ana@ejemplo.com"
    assert set(usuario) == {"id_usuario", "nombre", "apellido", "correo", "telefono", "rol"}


def test_me_refleja_el_rol_actual_de_la_base(app, client, repositorio):
    usuario = repositorio.agregar("ana@ejemplo.com")
    token = crear_token(app, usuario.id_usuario, CLIENTE)
    usuario.rol = EMPLEADO  # cambio de rol posterior a la emisión del token
    assert client.get("/api/auth/me", headers=cabecera_bearer(token)).get_json()["usuario"]["rol"] == "empleado"


def test_logout_con_token_responde_204(app, client, repositorio):
    usuario = repositorio.agregar("ana@ejemplo.com")
    respuesta = client.post("/api/auth/logout", headers=cabecera_bearer(crear_token(app, usuario.id_usuario)))
    assert respuesta.status_code == 204
    assert respuesta.get_data() == b""


def test_logout_sin_token_responde_401(client, repositorio):
    assert client.post("/api/auth/logout").status_code == 401


@pytest.mark.parametrize(
    "cabecera",
    [
        {},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer no.es.un-jwt"},
        {"Authorization": "Token abc"},
    ],
)
def test_token_ausente_o_mal_formado_401(client, repositorio, cabecera):
    respuesta = client.get("/api/auth/me", headers=cabecera)
    assert respuesta.status_code == 401
    assert _error(respuesta)["codigo"] == "no_autenticado"


def test_token_expirado_401(app, client, repositorio):
    usuario = repositorio.agregar("ana@ejemplo.com")
    token = crear_token(app, usuario.id_usuario, expires_delta=timedelta(seconds=-1))
    respuesta = client.get("/api/auth/me", headers=cabecera_bearer(token))
    assert respuesta.status_code == 401
    assert _error(respuesta)["codigo"] == "token_expirado"


def test_token_firmado_con_otra_clave_401(client, repositorio):
    repositorio.agregar("ana@ejemplo.com")
    falso = pyjwt.encode({"sub": "1", "type": "access", "fresh": False, "jti": "x",
                          "iat": 1, "nbf": 1, "exp": 4_000_000_000},
                         "otra-clave-cualquiera-de-32-caracteres!", algorithm="HS256")
    assert client.get("/api/auth/me", headers=cabecera_bearer(falso)).status_code == 401


def test_token_alterado_401(app, client, repositorio):
    usuario = repositorio.agregar("ana@ejemplo.com")
    token = crear_token(app, usuario.id_usuario)
    cabecera, carga, firma = token.split(".")
    alterado = ".".join([cabecera, carga, firma[:-2] + ("AA" if firma[-2:] != "AA" else "BB")])
    assert client.get("/api/auth/me", headers=cabecera_bearer(alterado)).status_code == 401


def test_token_de_usuario_inexistente_401(app, client, repositorio):
    assert client.get("/api/auth/me", headers=cabecera_bearer(crear_token(app, 999))).status_code == 401


def test_token_de_usuario_desactivado_401(app, client, repositorio):
    usuario = repositorio.agregar("ana@ejemplo.com")
    token = crear_token(app, usuario.id_usuario)
    usuario.activo = False
    respuesta = client.get("/api/auth/me", headers=cabecera_bearer(token))
    assert respuesta.status_code == 401
    assert _error(respuesta)["codigo"] == "no_autenticado"


# ---------------------------------------------------------------------------
# Autorización por roles y propiedad de recursos
# ---------------------------------------------------------------------------

@pytest.fixture
def app_con_rutas_protegidas(app):
    @app.get("/api/_prueba/empleado")
    @requiere_rol(EMPLEADO)
    def _solo_empleado():
        return jsonify({"ok": True})

    @app.get("/api/_prueba/admin")
    @requiere_rol(ADMINISTRADOR)
    def _solo_admin():
        return jsonify({"ok": True})

    @app.get("/api/_prueba/recurso-de/<int:propietario>")
    @requiere_rol(CLIENTE)
    def _recurso(propietario):
        exigir_propietario(propietario)
        return jsonify({"ok": True})

    return app


@pytest.mark.parametrize(
    "rol, ruta, esperado",
    [
        ("cliente", "/api/_prueba/empleado", 403),
        ("empleado", "/api/_prueba/empleado", 200),
        ("administrador", "/api/_prueba/empleado", 200),
        ("cliente", "/api/_prueba/admin", 403),
        ("empleado", "/api/_prueba/admin", 403),
        ("administrador", "/api/_prueba/admin", 200),
    ],
)
def test_autorizacion_por_rol(app_con_rutas_protegidas, client, cabeceras, rol, ruta, esperado):
    respuesta = client.get(ruta, headers=cabeceras[rol])
    assert respuesta.status_code == esperado
    if esperado == 403:
        assert _error(respuesta)["codigo"] == "acceso_denegado"


def test_ruta_con_rol_sin_token_responde_401_no_403(app_con_rutas_protegidas, client, cabeceras):
    assert client.get("/api/_prueba/admin").status_code == 401


def test_rol_del_token_no_concede_permisos(app_con_rutas_protegidas, app, client, repositorio):
    # Token que dice "administrador", pero en la base el usuario es cliente.
    usuario = repositorio.agregar("ana@ejemplo.com", rol=CLIENTE)
    token = crear_token(app, usuario.id_usuario, ADMINISTRADOR)
    assert client.get("/api/_prueba/admin", headers=cabecera_bearer(token)).status_code == 403


def test_cambio_de_rol_tiene_efecto_inmediato(app_con_rutas_protegidas, app, client, repositorio):
    usuario = repositorio.agregar("jefe@ejemplo.com", rol=ADMINISTRADOR)
    token = crear_token(app, usuario.id_usuario, ADMINISTRADOR)
    assert client.get("/api/_prueba/admin", headers=cabecera_bearer(token)).status_code == 200
    usuario.rol = CLIENTE
    assert client.get("/api/_prueba/admin", headers=cabecera_bearer(token)).status_code == 403


@pytest.mark.parametrize("rol, propietario, esperado", [
    ("cliente", 1, 200),        # su propio recurso
    ("cliente", 7, 404),        # recurso ajeno: 404, no revela que existe
    ("administrador", 7, 200),  # el administrador accede a todo
])
def test_exigir_propietario(app_con_rutas_protegidas, client, cabeceras, rol, propietario, esperado):
    assert client.get(f"/api/_prueba/recurso-de/{propietario}", headers=cabeceras[rol]).status_code == esperado


def test_requiere_rol_sin_roles_es_error_de_programacion():
    with pytest.raises(ValueError):
        requiere_rol()
