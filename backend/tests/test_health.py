import psycopg
from psycopg_pool import PoolTimeout

from tests.conftest import PoolFalso

CLAVE_POOL = "fullbikers_db_pool"


def test_health_responde_sin_base_de_datos(client):
    respuesta = client.get("/api/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"estado": "OK", "servicio": "API FullBikers"}


def test_health_db_sin_configuracion_responde_503(client):
    respuesta = client.get("/api/health/db")
    assert respuesta.status_code == 503
    assert respuesta.get_json()["error"]["codigo"] == "base_de_datos_no_disponible"


def test_health_db_ejecuta_select_1(app, client):
    pool = PoolFalso()
    app.extensions[CLAVE_POOL] = pool
    respuesta = client.get("/api/health/db")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"estado": "OK", "base_de_datos": "disponible"}
    assert pool.conexion.ejecutadas[0][0] == "SELECT 1"


def test_health_db_con_error_de_conexion_no_expone_detalles(app, client):
    app.extensions[CLAVE_POOL] = PoolFalso(
        error=psycopg.OperationalError('connection to server at "ep-secreto.neon.tech" failed: password authentication failed')
    )
    respuesta = client.get("/api/health/db")
    assert respuesta.status_code == 503
    cuerpo = respuesta.get_data(as_text=True)
    assert "neon.tech" not in cuerpo and "password" not in cuerpo


def test_health_db_con_pool_agotado_responde_503(app, client):
    app.extensions[CLAVE_POOL] = PoolFalso(error=PoolTimeout("sin conexiones"))
    assert client.get("/api/health/db").status_code == 503
