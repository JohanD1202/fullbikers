"""Integración: autenticación, autorización, catálogo protegido y comandos
de consola de extremo a extremo (HTTP -> controlador -> servicio -> DAO -> PostgreSQL).
"""
import pytest

from app import create_app
from config import database
from models.usuario import ADMINISTRADOR

CONTRASENA = "Integracion2026"


def _registrar(cliente_http, correo, **extra):
    datos = {"nombre": "Ana", "apellido": "Pérez", "correo": correo, "contrasena": CONTRASENA, **extra}
    return cliente_http.post("/api/auth/register", json=datos)


def _login(cliente_http, correo, contrasena=CONTRASENA):
    return cliente_http.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _fila(conn, correo):
    return conn.execute("SELECT * FROM usuario WHERE correo = %s", (correo,)).fetchone()


def test_registro_guarda_cliente_con_hash(cliente_http, conn, correo_unico):
    correo = correo_unico("registro")
    respuesta = _registrar(cliente_http, correo.upper(), telefono="300 123 4567")
    assert respuesta.status_code == 201
    fila = _fila(conn, correo)
    assert fila["rol"] == "cliente" and fila["activo"] is True
    assert fila["contrasena_hash"].startswith("scrypt:") and CONTRASENA not in fila["contrasena_hash"]
    assert respuesta.get_json()["usuario"]["id_usuario"] == fila["id_usuario"]


def test_registro_duplicado_409(cliente_http, conn, correo_unico):
    correo = correo_unico("duplicado")
    assert _registrar(cliente_http, correo).status_code == 201
    respuesta = _registrar(cliente_http, "  " + correo.upper())
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["codigo"] == "correo_ya_registrado"
    assert conn.execute("SELECT count(*) AS n FROM usuario WHERE correo = %s", (correo,)).fetchone()["n"] == 1


def test_registro_como_administrador_rechazado(cliente_http, conn, correo_unico):
    correo = correo_unico("intruso")
    respuesta = _registrar(cliente_http, correo, rol=ADMINISTRADOR)
    assert respuesta.status_code == 400
    assert _fila(conn, correo) is None


def test_registro_invalido_no_inserta(cliente_http, conn, correo_unico):
    correo = correo_unico("invalido")
    assert _registrar(cliente_http, correo, telefono="abc").status_code == 400
    assert _fila(conn, correo) is None


def test_flujo_completo_login_me_catalogo_logout(cliente_http, correo_unico):
    correo = correo_unico("flujo")
    _registrar(cliente_http, correo)

    login = _login(cliente_http, correo.upper())
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    assert login.get_json()["usuario"]["rol"] == "cliente"

    me = cliente_http.get("/api/auth/me", headers=_bearer(token))
    assert me.status_code == 200 and me.get_json()["usuario"]["correo"] == correo

    principal = cliente_http.get("/api/principal", headers=_bearer(token))
    assert principal.status_code == 200 and principal.get_json()["total_productos"] == 11

    productos = cliente_http.get("/api/productos?busqueda=casco&por_pagina=2&pagina=2", headers=_bearer(token))
    cuerpo = productos.get_json()
    assert (cuerpo["total_resultados"], cuerpo["total_paginas"], len(cuerpo["productos"])) == (3, 2, 1)

    id_producto = cuerpo["productos"][0]["id_producto"]
    detalle = cliente_http.get(f"/api/productos/{id_producto}", headers=_bearer(token))
    assert detalle.status_code == 200 and detalle.get_json()["variantes"]

    assert cliente_http.post("/api/auth/logout", headers=_bearer(token)).status_code == 204


@pytest.mark.parametrize("ruta", ["/api/principal", "/api/productos", "/api/productos/1", "/api/auth/me"])
def test_sin_token_401(cliente_http, ruta):
    assert cliente_http.get(ruta).status_code == 401


def test_credenciales_incorrectas_401(cliente_http, correo_unico):
    correo = correo_unico("mala")
    _registrar(cliente_http, correo)
    respuesta = _login(cliente_http, correo, "Incorrecta2026")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"]["codigo"] == "credenciales_invalidas"


def test_usuario_desactivado_pierde_acceso(cliente_http, conn, correo_unico):
    correo = correo_unico("inactivo")
    _registrar(cliente_http, correo)
    token = _login(cliente_http, correo).get_json()["access_token"]

    conn.execute("UPDATE usuario SET activo = false WHERE correo = %s", (correo,))
    assert cliente_http.get("/api/productos", headers=_bearer(token)).status_code == 401
    respuesta = _login(cliente_http, correo)
    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"]["codigo"] == "credenciales_invalidas"


def test_cambio_de_rol_se_lee_de_la_base(cliente_http, conn, correo_unico):
    correo = correo_unico("ascenso")
    _registrar(cliente_http, correo)
    token = _login(cliente_http, correo).get_json()["access_token"]
    conn.execute("UPDATE usuario SET rol = 'empleado' WHERE correo = %s", (correo,))
    assert cliente_http.get("/api/auth/me", headers=_bearer(token)).get_json()["usuario"]["rol"] == "empleado"
    # El empleado también consulta el catálogo.
    assert cliente_http.get("/api/productos", headers=_bearer(token)).status_code == 200


def test_limitador_de_intentos(cliente_http, correo_unico):
    correo = correo_unico("fuerza")
    _registrar(cliente_http, correo)
    for _ in range(5):
        assert _login(cliente_http, correo, "Incorrecta2026").status_code == 401
    assert _login(cliente_http, correo).status_code == 429


def test_comando_crear_admin(app_bd, conn, correo_unico):
    correo = correo_unico("admin")
    entrada = f"Laura\nGómez\n{correo}\n\n{CONTRASENA}\n{CONTRASENA}\n"
    resultado = app_bd.test_cli_runner().invoke(args=["crear-admin"], input=entrada)
    assert resultado.exit_code == 0, resultado.output
    fila = _fila(conn, correo)
    assert (fila["rol"], fila["activo"]) == ("administrador", True)

    # Inicia sesión y accede como administrador.
    cliente_http = app_bd.test_client()
    token = _login(cliente_http, correo).get_json()["access_token"]
    assert cliente_http.get("/api/productos", headers=_bearer(token)).status_code == 200

    # Repetir con el mismo correo no crea ni modifica nada.
    repetido = app_bd.test_cli_runner().invoke(args=["crear-admin"], input=entrada)
    assert repetido.exit_code == 1
    assert conn.execute("SELECT count(*) AS n FROM usuario WHERE correo = %s", (correo,)).fetchone()["n"] == 1


def test_comando_crear_admin_no_promueve_cliente(app_bd, cliente_http, conn, correo_unico):
    correo = correo_unico("cliente-existente")
    _registrar(cliente_http, correo)
    entrada = f"Laura\nGómez\n{correo}\n\n{CONTRASENA}\n{CONTRASENA}\n"
    assert app_bd.test_cli_runner().invoke(args=["crear-admin"], input=entrada).exit_code == 1
    assert _fila(conn, correo)["rol"] == "cliente"


def test_comando_usuarios_prueba_tres_roles_sin_duplicar(url_bd, conn, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url_bd)
    app = create_app("development")
    try:
        for _ in range(2):
            resultado = app.test_cli_runner().invoke(args=["crear-usuarios-prueba"],
                                                     input=f"{CONTRASENA}\n{CONTRASENA}\n")
            assert resultado.exit_code == 0, resultado.output
    finally:
        database.cerrar_pool(app)
    filas = conn.execute(
        "SELECT correo, rol, count(*) OVER (PARTITION BY correo) AS n FROM usuario WHERE correo LIKE '%@fullbikers.test'"
    ).fetchall()
    assert {f["correo"]: f["rol"] for f in filas} == {
        "cliente@fullbikers.test": "cliente",
        "empleado@fullbikers.test": "empleado",
        "admin@fullbikers.test": "administrador",
    }
    assert all(f["n"] == 1 for f in filas)
