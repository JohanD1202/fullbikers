"""Pruebas de INTEGRACIÓN contra un PostgreSQL local real.

Requisitos (ver backend/README.md §7):
  * Un clúster local TEMPORAL con schema.sql, permissions.sql y seed_dev.sql
    aplicados sobre la base "fullbikers".
  * TEST_DATABASE_URL con el rol fullbikers_app, por ejemplo:
        postgresql://fullbikers_app:<clave>@localhost:55433/fullbikers

Sin TEST_DATABASE_URL todas estas pruebas se omiten. Por seguridad solo se
aceptan servidores en localhost: nunca se ejecutan contra Neon (las pruebas
insertan usuarios y no pueden borrarlos, porque el rol no tiene DELETE).
"""
import os
import uuid
from urllib.parse import urlsplit

import psycopg
import pytest
from psycopg.rows import dict_row

from app import create_app
from config import database

URL = os.getenv("TEST_DATABASE_URL", "").strip()
_HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integracion" in item.nodeid.replace("\\", "/").split("/"):
            item.add_marker(pytest.mark.integracion)
            if not URL:
                item.add_marker(pytest.mark.skip(reason="TEST_DATABASE_URL no definida"))


def _validar_url():
    host = urlsplit(URL).hostname
    if host not in _HOSTS_LOCALES:
        pytest.exit(f"TEST_DATABASE_URL debe apuntar a localhost (recibido: {host}). Nunca a Neon.", returncode=2)


@pytest.fixture(scope="session")
def url_bd():
    _validar_url()
    return URL


@pytest.fixture(scope="session")
def app_bd(url_bd):
    """Aplicación real (controladores, servicios, DAO y pool) sobre la base local."""
    app = create_app("testing")
    app.config["DATABASE_URL"] = url_bd
    database.init_app(app)
    yield app
    database.cerrar_pool(app)


@pytest.fixture
def cliente_http(app_bd):
    return app_bd.test_client()


@pytest.fixture
def conn(url_bd):
    """Conexión directa como fullbikers_app, en autocommit."""
    with psycopg.connect(url_bd, row_factory=dict_row, autocommit=True) as conexion:
        yield conexion


@pytest.fixture
def correo_unico():
    """Correos distintos en cada ejecución: el rol de la API no puede borrar filas."""
    return lambda prefijo="usuario": f"{prefijo}.{uuid.uuid4().hex[:10]}@prueba.test"
