"""Integración: rol fullbikers_app, permisos efectivos, identidades y restricciones."""
import uuid
from decimal import Decimal

import pytest
from psycopg import errors

TABLAS = ("usuario", "direccion", "categoria", "producto", "variante_producto", "carrito",
          "detalle_carrito", "pedido", "detalle_pedido", "movimiento_inventario")
HISTORICOS = ("detalle_pedido", "movimiento_inventario")


def _uno(conn, sql, params=None):
    return conn.execute(sql, params).fetchone()


def test_conecta_como_rol_de_la_api(conn):
    assert _uno(conn, "SELECT current_user AS u")["u"] == "fullbikers_app"


def test_atributos_del_rol(conn):
    rol = _uno(conn, "SELECT * FROM pg_roles WHERE rolname = 'fullbikers_app'")
    assert rol["rolcanlogin"] is True
    assert rol["rolconnlimit"] == 30
    for atributo in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolinherit", "rolreplication", "rolbypassrls"):
        assert rol[atributo] is False, atributo
    miembro_de = conn.execute(
        "SELECT r.rolname FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.roleid "
        "JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = 'fullbikers_app'"
    ).fetchall()
    assert miembro_de == []


def test_existen_las_diez_tablas(conn):
    filas = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    ).fetchall()
    assert sorted(f["table_name"] for f in filas) == sorted(TABLAS)


@pytest.mark.parametrize("tabla", TABLAS)
def test_privilegios_efectivos_por_tabla(conn, tabla):
    def tiene(privilegio):
        return _uno(conn, "SELECT has_table_privilege(current_user, %s, %s) AS p", (tabla, privilegio))["p"]

    assert tiene("SELECT") and tiene("INSERT")
    assert tiene("UPDATE") is (tabla not in HISTORICOS)
    for prohibido in ("DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
        assert tiene(prohibido) is False, prohibido


@pytest.mark.parametrize("tabla", HISTORICOS)
def test_historicos_solo_actualizan_activo(conn, tabla):
    columnas = conn.execute(
        "SELECT column_name, has_column_privilege(current_user, %s, column_name, 'UPDATE') AS puede "
        "FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
        (tabla, tabla),
    ).fetchall()
    assert {c["column_name"] for c in columnas if c["puede"]} == {"activo"}


@pytest.mark.parametrize(
    "sentencia",
    [
        "DELETE FROM usuario WHERE false",
        "DELETE FROM producto WHERE false",
        "TRUNCATE categoria",
        "CREATE TABLE public.tabla_no_permitida (id int)",
        "ALTER TABLE usuario ADD COLUMN columna_no_permitida int",
        "DROP TABLE carrito",
        "CREATE INDEX ix_no_permitido ON producto (marca)",
        "UPDATE detalle_pedido SET cantidad = 1 WHERE false",
        "UPDATE movimiento_inventario SET stock_nuevo = 0 WHERE false",
    ],
)
def test_operaciones_prohibidas(conn, sentencia):
    with pytest.raises(errors.InsufficientPrivilege):
        conn.execute(sentencia)


def test_borrado_logico_en_historicos_permitido(conn):
    conn.execute("UPDATE detalle_pedido SET activo = activo WHERE false")
    conn.execute("UPDATE movimiento_inventario SET activo = activo WHERE false")


def test_privilegios_heredados_de_public(conn):
    """PUBLIC conserva CONNECT y TEMPORARY en la base y USAGE (sin CREATE) en public;
    no tiene ningún privilegio sobre las tablas."""
    privilegios = _uno(conn, """
        SELECT has_database_privilege(current_user, current_database(), 'CONNECT')   AS connect,
               has_database_privilege(current_user, current_database(), 'CREATE')    AS create_base,
               has_database_privilege(current_user, current_database(), 'TEMPORARY') AS temporary,
               has_schema_privilege(current_user, 'public', 'USAGE')                 AS usage_esquema,
               has_schema_privilege(current_user, 'public', 'CREATE')                AS create_esquema
    """)
    assert privilegios == {"connect": True, "create_base": False, "temporary": True,
                           "usage_esquema": True, "create_esquema": False}
    publicos_en_tablas = conn.execute(
        "SELECT table_name FROM information_schema.role_table_grants "
        "WHERE table_schema = 'public' AND grantee = 'PUBLIC'"
    ).fetchall()
    assert publicos_en_tablas == []
    # TEMPORARY (heredado de PUBLIC) solo permite tablas temporales propias.
    conn.execute("CREATE TEMP TABLE tmp_prueba (id int)")


def test_sin_usage_en_secuencias_pero_identidad_funciona(conn):
    secuencias = conn.execute(
        "SELECT has_sequence_privilege(current_user, schemaname || '.' || sequencename, 'USAGE') AS usage "
        "FROM pg_sequences WHERE schemaname = 'public'"
    ).fetchall()
    assert len(secuencias) == 10 and not any(s["usage"] for s in secuencias)

    nombre = f"Prueba identidad {uuid.uuid4().hex[:8]}"
    with conn.transaction(force_rollback=True):
        primero = _uno(conn, "INSERT INTO categoria (nombre, activo) VALUES (%s, false) RETURNING id_categoria",
                       (nombre,))["id_categoria"]
        segundo = _uno(conn, "INSERT INTO categoria (nombre, activo) VALUES (%s, false) RETURNING id_categoria",
                       (nombre + " B",))["id_categoria"]
    assert segundo > primero


def test_identidad_generated_always_rechaza_id_explicito(conn):
    with pytest.raises(errors.GeneratedAlways):
        conn.execute("INSERT INTO categoria (id_categoria, nombre) VALUES (999999, 'Explícita')")


@pytest.mark.parametrize(
    "sentencia, error",
    [
        ("INSERT INTO usuario (nombre, apellido, correo, contrasena_hash) "
         "VALUES ('A', 'B', 'Mayus@Ejemplo.com', repeat('h', 30))", errors.CheckViolation),
        ("INSERT INTO usuario (nombre, apellido, correo, contrasena_hash, rol) "
         "VALUES ('A', 'B', 'x@ejemplo.com', repeat('h', 30), 'visitante')", errors.CheckViolation),
        ("INSERT INTO usuario (nombre, apellido, correo, contrasena_hash) "
         "VALUES ('A', 'B', 'x@ejemplo.com', 'corto')", errors.CheckViolation),
        ("INSERT INTO producto (id_categoria, nombre, referencia, precio) "
         "VALUES (2147483647, 'X', 'REF-INEXISTENTE', 1)", errors.ForeignKeyViolation),
        ("INSERT INTO producto (id_categoria, nombre, referencia, precio) "
         "SELECT id_categoria, 'X', 'CAS-INT-001', 1 FROM categoria LIMIT 1", errors.UniqueViolation),
        ("INSERT INTO producto (id_categoria, nombre, referencia, precio) "
         "SELECT id_categoria, 'X', 'REF-NEGATIVO', -1 FROM categoria LIMIT 1", errors.CheckViolation),
        ("INSERT INTO categoria (nombre) VALUES ('CASCOS')", errors.UniqueViolation),
        ("INSERT INTO variante_producto (id_producto, sku, stock) "
         "SELECT id_producto, 'SKU-NEG', -1 FROM producto LIMIT 1", errors.CheckViolation),
    ],
)
def test_restricciones_e_integridad_referencial(conn, sentencia, error):
    with pytest.raises(error):
        with conn.transaction():
            conn.execute(sentencia)


def test_precision_de_precios(conn):
    """NUMERIC(14,2): el valor máximo y los centavos se conservan exactos."""
    referencia = f"PRE-{uuid.uuid4().hex[:8].upper()}"
    with conn.transaction(force_rollback=True):  # no deja un producto sin variantes
        fila = _uno(conn, """
        INSERT INTO producto (id_categoria, nombre, referencia, precio, activo)
        SELECT id_categoria, 'Producto de precisión', %s, %s, false
        FROM categoria WHERE nombre = 'Repuestos'
        RETURNING precio, precio * 3 AS triple
        """, (referencia, Decimal("999999999999.99")))
    assert fila["precio"] == Decimal("999999999999.99")
    assert fila["triple"] == Decimal("2999999999999.97")
    assert _uno(conn, "SELECT 0.1::numeric(14,2) + 0.2::numeric(14,2) AS s")["s"] == Decimal("0.30")
    with pytest.raises(errors.NumericValueOutOfRange):
        conn.execute("SELECT 1000000000000.00::numeric(14,2)")
