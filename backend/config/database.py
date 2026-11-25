"""Conexión a PostgreSQL (Neon) mediante Psycopg 3 y un pool de conexiones.

Uso desde la capa de servicios:

    from config import database

    # Lecturas (o una sola sentencia):
    with database.obtener_conexion() as conn:
        productos = ProductoDAO.listar_catalogo(conn, ...)

    # Operación de negocio con varias escrituras: una sola transacción
    # compartida por todos los DAO que reciben la misma conexión.
    with database.transaccion() as conn:
        PedidoDAO.crear(conn, ...)
        InventarioDAO.registrar_salida(conn, ...)

Reglas:
  * Los DAO reciben la conexión como primer argumento y NUNCA llaman a
    commit() ni rollback(): la transacción la controla el servicio.
  * Al salir del bloque se confirma la transacción si no hubo excepción y se
    revierte si la hubo; la conexión vuelve al pool.
"""
import atexit
import logging
from contextlib import contextmanager

import psycopg
from flask import current_app
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from exceptions import BaseDeDatosNoDisponibleError

logger = logging.getLogger(__name__)

_EXTENSION = "fullbikers_db_pool"
# Una conexión inactiva por encima del mínimo se cierra tras este tiempo (s).
_MAX_IDLE_SEGUNDOS = 300


def init_app(app):
    """Crea el pool (sin conectarse todavía) y lo registra en la aplicación.

    Si DATABASE_URL no está definida, la aplicación arranca igualmente y los
    endpoints que usan la base responden 503.
    """
    url = app.config.get("DATABASE_URL")
    if not url:
        app.extensions[_EXTENSION] = None
        if not app.testing:
            logger.warning("DATABASE_URL no está configurada: los endpoints que usan la base responderán 503.")
        return

    pool = ConnectionPool(
        conninfo=url,
        min_size=app.config["DB_POOL_MIN_SIZE"],
        max_size=app.config["DB_POOL_MAX_SIZE"],
        timeout=app.config["DB_CONNECT_TIMEOUT"],
        max_idle=_MAX_IDLE_SEGUNDOS,
        kwargs={
            "row_factory": dict_row,
            "connect_timeout": app.config["DB_CONNECT_TIMEOUT"],
            "application_name": "fullbikers-api",
        },
        # Descarta conexiones cerradas por el servidor (p. ej., Neon suspendido).
        check=ConnectionPool.check_connection,
        name="fullbikers",
        open=False,
    )
    # wait=False: la API arranca aunque PostgreSQL no esté disponible.
    pool.open(wait=False)
    app.extensions[_EXTENSION] = pool
    atexit.register(pool.close)
    logger.info(
        "Pool de PostgreSQL creado (min=%s, max=%s).",
        app.config["DB_POOL_MIN_SIZE"],
        app.config["DB_POOL_MAX_SIZE"],
    )


def cerrar_pool(app):
    pool = app.extensions.get(_EXTENSION)
    if pool is not None:
        pool.close()


def _obtener_pool():
    pool = current_app.extensions.get(_EXTENSION)
    if pool is None:
        raise BaseDeDatosNoDisponibleError("DATABASE_URL no está configurada.")
    return pool


@contextmanager
def obtener_conexion():
    """Presta una conexión del pool durante el bloque `with`."""
    pool = _obtener_pool()
    try:
        # pool.connection() confirma al salir sin error, revierte si hubo
        # excepción y devuelve la conexión al pool en ambos casos.
        with pool.connection() as conexion:
            yield conexion
    except PoolTimeout as exc:
        raise BaseDeDatosNoDisponibleError("No se obtuvo una conexión del pool a tiempo.") from exc


@contextmanager
def transaccion():
    """Conexión con una transacción explícita para operaciones de negocio."""
    with obtener_conexion() as conexion:
        with conexion.transaction():
            yield conexion


def verificar_conexion():
    """Ejecuta SELECT 1. Lanza BaseDeDatosNoDisponibleError si falla."""
    try:
        with obtener_conexion() as conexion:
            conexion.execute("SELECT 1").fetchone()
    except psycopg.Error as exc:
        raise BaseDeDatosNoDisponibleError("PostgreSQL no respondió a SELECT 1.") from exc
