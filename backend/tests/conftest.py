"""Utilidades comunes de las pruebas.

Pruebas UNITARIAS (tests/*.py): no se conectan a PostgreSQL ni a Neon. La
configuración "testing" fuerza DATABASE_URL = None y las conexiones o la
tabla usuario se sustituyen por dobles en memoria.

Pruebas de INTEGRACIÓN (tests/integracion/): usan un PostgreSQL local real
indicado en TEST_DATABASE_URL; ver tests/integracion/conftest.py.
"""
from contextlib import contextmanager

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from config import database
from dao.usuario_dao import UsuarioDAO
from models.usuario import ADMINISTRADOR, CLIENTE, EMPLEADO, Usuario
from services import usuario_service

VARIABLES_DE_ENTORNO = (
    "APP_ENV", "SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS",
    "DB_POOL_MIN_SIZE", "DB_POOL_MAX_SIZE", "DB_CONNECT_TIMEOUT", "LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    """Evita que variables del sistema o de un .env local afecten las pruebas.

    create_app() no carga backend/.env durante las pruebas: así nunca se usan
    los secretos ni la DATABASE_URL real (Neon) de un desarrollador.
    """
    import app as modulo_app

    monkeypatch.setattr(modulo_app, "load_dotenv", lambda *args, **kwargs: False)
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


# ---------------------------------------------------------------------------
# Autenticación en pruebas unitarias
# ---------------------------------------------------------------------------

def crear_token(app, id_usuario, rol=CLIENTE, **kwargs):
    """JWT firmado con la clave de pruebas, igual al que emite /api/auth/login."""
    with app.app_context():
        return create_access_token(identity=str(id_usuario), additional_claims={"rol": rol}, **kwargs)


def cabecera_bearer(token):
    return {"Authorization": f"Bearer {token}"}


USUARIOS_FIJOS = {
    1: Usuario(1, "Ana", "Cliente", "cliente@fullbikers.test", CLIENTE),
    2: Usuario(2, "Eva", "Empleado", "empleado@fullbikers.test", EMPLEADO),
    3: Usuario(3, "Luis", "Admin", "admin@fullbikers.test", ADMINISTRADOR),
}
ID_POR_ROL = {CLIENTE: 1, EMPLEADO: 2, ADMINISTRADOR: 3}


@pytest.fixture
def usuarios_autenticables(monkeypatch):
    """El middleware encuentra a los usuarios 1 (cliente), 2 (empleado) y 3 (admin).

    Útil para probar controladores protegidos sin tocar la base de datos.
    """
    monkeypatch.setattr(usuario_service, "obtener_usuario_activo", USUARIOS_FIJOS.get)
    return USUARIOS_FIJOS


@pytest.fixture
def cabeceras(app, usuarios_autenticables):
    """Cabeceras Authorization por rol: cabeceras["cliente"], ["empleado"], ["administrador"]."""
    return {rol: cabecera_bearer(crear_token(app, id_usuario, rol)) for rol, id_usuario in ID_POR_ROL.items()}


class RepositorioUsuariosFalso:
    """Tabla usuario en memoria: sustituye UsuarioDAO y la conexión del pool."""

    def __init__(self):
        self.filas = {}
        self.siguiente_id = 1

    @contextmanager
    def conexion(self):
        yield None

    def agregar(self, correo, contrasena="Clave2026", rol=CLIENTE, activo=True):
        usuario = self.crear(None, "Nombre", "Apellido", correo, generate_password_hash(contrasena), None, rol)
        usuario.activo = activo
        return usuario

    def obtener_por_correo(self, _conn, correo):
        return next((u for u in self.filas.values() if u.correo == correo), None)

    def obtener_por_id(self, _conn, id_usuario):
        return self.filas.get(id_usuario)

    def existe_correo_de_otro(self, _conn, correo, id_usuario):
        return any(u.correo == correo and u.id_usuario != id_usuario for u in self.filas.values())

    def actualizar_datos_personales(self, _conn, id_usuario, cambios):
        usuario = self.filas.get(id_usuario)
        if usuario is None or not usuario.activo:
            return None
        for campo, valor in cambios.items():
            setattr(usuario, campo, valor)
        return usuario

    def crear(self, _conn, nombre, apellido, correo, contrasena_hash, telefono, rol):
        usuario = Usuario(self.siguiente_id, nombre, apellido, correo, rol, True, telefono, contrasena_hash)
        self.filas[usuario.id_usuario] = usuario
        self.siguiente_id += 1
        return usuario


@pytest.fixture
def repositorio(monkeypatch):
    repo = RepositorioUsuariosFalso()
    monkeypatch.setattr(database, "transaccion", repo.conexion)
    monkeypatch.setattr(database, "obtener_conexion", repo.conexion)
    monkeypatch.setattr(UsuarioDAO, "obtener_por_correo", staticmethod(repo.obtener_por_correo))
    monkeypatch.setattr(UsuarioDAO, "obtener_por_id", staticmethod(repo.obtener_por_id))
    monkeypatch.setattr(UsuarioDAO, "crear", staticmethod(repo.crear))
    monkeypatch.setattr(UsuarioDAO, "existe_correo_de_otro", staticmethod(repo.existe_correo_de_otro))
    monkeypatch.setattr(UsuarioDAO, "actualizar_datos_personales", staticmethod(repo.actualizar_datos_personales))
    return repo
