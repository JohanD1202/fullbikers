import pytest

from app import create_app
from config.settings import ConfiguracionInvalidaError

SECRETO_A = "Zq8vN3rT6yW1pL4sK7dF0gH2jM5bX9cV-a1"
SECRETO_B = "Rf2kP9wQ4tY7uI0oA3sD6fG8hJ1lZ5xC-b2"
URL_FALSA = "postgresql://usuario:clave@127.0.0.1:1/bd?sslmode=require"


def _entorno_produccion(monkeypatch, **cambios):
    valores = {
        "SECRET_KEY": SECRETO_A,
        "JWT_SECRET_KEY": SECRETO_B,
        "DATABASE_URL": URL_FALSA,
        "CORS_ORIGINS": "https://fullbikers.netlify.app",
    }
    valores.update(cambios)
    for nombre, valor in valores.items():
        if valor is None:
            monkeypatch.delenv(nombre, raising=False)
        else:
            monkeypatch.setenv(nombre, valor)


def test_factory_crea_app_de_pruebas(app):
    assert app.config["TESTING"] is True
    assert app.config["APP_ENV"] == "testing"
    assert app.config["DATABASE_URL"] is None


def test_pruebas_ignoran_database_url_del_entorno(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL_FALSA)
    app = create_app("testing")
    assert app.config["DATABASE_URL"] is None


def test_desarrollo_arranca_sin_database_url():
    app = create_app("development")
    assert app.config["DEBUG"] is False
    assert len(app.config["SECRET_KEY"]) >= 32
    assert app.test_client().get("/api/health").status_code == 200


def test_entorno_desconocido_es_rechazado():
    with pytest.raises(ConfiguracionInvalidaError):
        create_app("staging")


def test_app_env_selecciona_el_entorno(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    assert create_app().config["APP_ENV"] == "testing"


@pytest.mark.parametrize(
    "cambios",
    [
        {"SECRET_KEY": None},
        {"JWT_SECRET_KEY": None},
        {"SECRET_KEY": "corta"},
        {"SECRET_KEY": "cambiar-esta-clave-por-una-segura-0000000"},
        {"JWT_SECRET_KEY": SECRETO_A},
        {"DATABASE_URL": None},
        {"DATABASE_URL": "postgresql://u:c@h/bd"},
        {"CORS_ORIGINS": "*"},
    ],
)
def test_produccion_rechaza_configuracion_insegura(monkeypatch, cambios):
    _entorno_produccion(monkeypatch, **cambios)
    with pytest.raises(ConfiguracionInvalidaError) as error:
        create_app("production")
    # El mensaje nunca incluye los valores de los secretos.
    assert SECRETO_A not in str(error.value)
    assert "clave@" not in str(error.value)


def test_produccion_registra_catalogo_protegido(monkeypatch):
    _entorno_produccion(monkeypatch)
    app = create_app("production")
    try:
        rutas = {regla.rule for regla in app.url_map.iter_rules()}
        assert {"/api/health", "/api/auth/login", "/api/auth/register", "/api/productos", "/api/principal"} <= rutas
        # Sin token: 401 antes de tocar la base de datos.
        respuesta = app.test_client().get("/api/productos")
        assert respuesta.status_code == 401
        assert respuesta.get_json()["error"]["codigo"] == "no_autenticado"
    finally:
        from config import database
        database.cerrar_pool(app)


def test_jwt_configurado_a_60_minutos(app):
    assert app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds() == 3600
    assert app.config["JWT_TOKEN_LOCATION"] == ["headers"]


def test_pool_invalido_rechazado(monkeypatch):
    monkeypatch.setenv("DB_POOL_MIN_SIZE", "6")
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "5")
    with pytest.raises(ConfiguracionInvalidaError):
        create_app("development")


def test_cors_permite_solo_origenes_configurados(client):
    permitido = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    ajeno = client.get("/api/health", headers={"Origin": "https://sitio-ajeno.example"})
    assert permitido.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in ajeno.headers
