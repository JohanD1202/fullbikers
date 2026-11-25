import psycopg
import pytest
from psycopg import errors

from exceptions import ApiError


@pytest.fixture
def app_con_rutas_de_error(app):
    @app.get("/api/_prueba/no-controlado")
    def _no_controlado():
        raise RuntimeError("detalle-interno-secreto")

    @app.get("/api/_prueba/sql")
    def _sql():
        raise errors.UndefinedColumn('column "estado" does not exist')

    @app.get("/api/_prueba/conexion")
    def _conexion():
        raise psycopg.OperationalError("connection to server at \"host-interno\" failed")

    @app.get("/api/_prueba/api-error")
    def _api_error():
        raise ApiError("Mensaje para el usuario.", codigo="regla_de_negocio", status_code=409)

    return app


def _error(respuesta):
    cuerpo = respuesta.get_json()
    assert set(cuerpo) == {"error"}
    return cuerpo["error"]


def test_ruta_inexistente_devuelve_json_404(client):
    respuesta = client.get("/api/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.is_json
    assert _error(respuesta)["codigo"] == "recurso_no_encontrado"


def test_metodo_no_permitido_devuelve_json_405(client):
    respuesta = client.post("/api/health")
    assert respuesta.status_code == 405
    assert _error(respuesta)["codigo"] == "metodo_no_permitido"


def test_error_no_controlado_devuelve_500_sin_detalles(app_con_rutas_de_error):
    respuesta = app_con_rutas_de_error.test_client().get("/api/_prueba/no-controlado")
    assert respuesta.status_code == 500
    assert _error(respuesta)["codigo"] == "error_interno"
    assert "detalle-interno-secreto" not in respuesta.get_data(as_text=True)
    assert "Traceback" not in respuesta.get_data(as_text=True)


def test_error_sql_devuelve_500_sin_exponer_la_consulta(app_con_rutas_de_error):
    respuesta = app_con_rutas_de_error.test_client().get("/api/_prueba/sql")
    assert respuesta.status_code == 500
    assert "estado" not in respuesta.get_data(as_text=True)


def test_error_de_conexion_devuelve_503(app_con_rutas_de_error):
    respuesta = app_con_rutas_de_error.test_client().get("/api/_prueba/conexion")
    assert respuesta.status_code == 503
    assert "host-interno" not in respuesta.get_data(as_text=True)


def test_api_error_conserva_codigo_mensaje_y_estado(app_con_rutas_de_error):
    respuesta = app_con_rutas_de_error.test_client().get("/api/_prueba/api-error")
    assert respuesta.status_code == 409
    assert _error(respuesta) == {"codigo": "regla_de_negocio", "mensaje": "Mensaje para el usuario."}


def test_logs_ocultan_credenciales():
    from config.logs import ocultar_datos_sensibles

    texto = ocultar_datos_sensibles(
        "url=postgresql://fullbikers_app:SuperClave123@ep-x.neon.tech/fullbikers password=otra "
        "Authorization: Bearer eyJhbGciOi.abc.def"
    )
    assert "SuperClave123" not in texto
    assert "password=otra" not in texto
    assert "eyJhbGciOi" not in texto
