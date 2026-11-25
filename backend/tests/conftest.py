"""Utilidades comunes de las pruebas.

Ninguna prueba se conecta a PostgreSQL ni a Neon: la configuración "testing"
fuerza DATABASE_URL = None y las conexiones se sustituyen por dobles en memoria.
"""
from contextlib import contextmanager

import pytest

from app import create_app

VARIABLES_DE_ENTORNO = (
    "APP_ENV", "SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS",
    "DB_POOL_MIN_SIZE", "DB_POOL_MAX_SIZE", "DB_CONNECT_TIMEOUT", "LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    """Evita que variables del sistema o de un .env local afecten las pruebas."""
    for nombre in VARIABLES_DE_ENTORNO:
        monkeypatch.delenv(nombre, raising=False)


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


class CursorFalso:
    """Cursor en memoria: registra las sentencias y devuelve resultados preparados."""

    def __init__(self, resultados):
        self.resultados = list(resultados)
        self.ejecutadas = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        self.ejecutadas.append((query, params))
        return self

    def fetchall(self):
        return self.resultados.pop(0)

    def fetchone(self):
        resultado = self.resultados.pop(0)
        return resultado[0] if isinstance(resultado, list) and resultado else (resultado or None)


class ConexionFalsa:
    def __init__(self, resultados=()):
        self.cursor_falso = CursorFalso(resultados)

    def cursor(self):
        return self.cursor_falso

    def execute(self, query, params=None):
        return self.cursor_falso.execute(query, params)

    @property
    def ejecutadas(self):
        return self.cursor_falso.ejecutadas


class PoolFalso:
    """Sustituye a psycopg_pool.ConnectionPool en app.extensions."""

    def __init__(self, conexion=None, error=None):
        self.conexion = conexion or ConexionFalsa([[{"?column?": 1}]])
        self.error = error

    @contextmanager
    def connection(self, timeout=None):
        if self.error:
            raise self.error
        yield self.conexion

    def close(self):
        pass
