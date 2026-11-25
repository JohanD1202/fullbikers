"""Integración (PostgreSQL real): registro y consulta de pedidos (RF-16 a RF-19).

Incluye reversión ante fallos y concurrencia real (dos hilos con conexiones
distintas del pool).
"""
import threading
from decimal import Decimal

import pytest

from dao.carrito_dao import CarritoDAO
from dao.inventario_dao import InventarioDAO
from dao.pedido_dao import PedidoDAO
# Fixtures compartidas con las pruebas del carrito (usuarios y producto propio).
from tests.integracion.test_bd_direcciones_carrito import (  # noqa: F401
    DIRECCION, nueva_sesion, producto_prueba, sesion,
)


def _codigo(respuesta):
    return respuesta.get_json()["error"]["codigo"]


def _agregar(cliente_http, cabeceras, id_producto, id_variante, cantidad):
    respuesta = cliente_http.post("/api/carrito/items", headers=cabeceras,
                                  json={"id_producto": id_producto, "id_variante": id_variante, "cantidad": cantidad})
    assert respuesta.status_code == 200, respuesta.get_json()
    return respuesta.get_json()["carrito"]


def _direccion(cliente_http, cabeceras, **cambios):
    respuesta = cliente_http.post("/api/direcciones", headers=cabeceras, json={**DIRECCION, **cambios})
    return respuesta.get_json()["direccion"]["id_direccion"]


def _confirmar(cliente_http, cabeceras, id_direccion, **extra):
    return cliente_http.post("/api/pedidos", headers=cabeceras, json={"id_direccion": id_direccion, **extra})


def _foto(conn, id_usuario, ids_variante):
    """Estado relevante para comprobar que nada cambió."""
    stock = conn.execute("SELECT id_variante, stock FROM variante_producto WHERE id_variante = ANY(%s) "
                         "ORDER BY id_variante", (list(ids_variante),)).fetchall()
    return {
        "stock": [(f["id_variante"], f["stock"]) for f in stock],
        "pedidos": conn.execute("SELECT count(*) AS n FROM pedido WHERE id_usuario = %s",
                                (id_usuario,)).fetchone()["n"],
        "movimientos": conn.execute("SELECT count(*) AS n FROM movimiento_inventario WHERE id_variante = ANY(%s)",
                                    (list(ids_variante),)).fetchone()["n"],
        "carrito_abierto": conn.execute("SELECT count(*) AS n FROM carrito WHERE id_usuario = %s AND estado = 'abierto'",
                                        (id_usuario,)).fetchone()["n"],
        "lineas": conn.execute(
            "SELECT count(*) AS n FROM detalle_carrito dc JOIN carrito c USING (id_carrito) "
            "WHERE c.id_usuario = %s AND c.estado = 'abierto' AND dc.activo", (id_usuario,)).fetchone()["n"],
    }


@pytest.fixture
def variante_base(conn):
    return conn.execute("SELECT id_variante, id_producto FROM variante_producto WHERE sku = 'ACC-SOP-001'").fetchone()


@pytest.fixture
def carrito_listo(cliente_http, sesion, producto_prueba):
    """Cliente con dirección y carrito: A x2 y B x1 del producto de prueba (33333.33 c/u)."""
    cabeceras, id_usuario, _ = sesion
    _agregar(cliente_http, cabeceras, producto_prueba["id_producto"], producto_prueba["A"], 2)
    _agregar(cliente_http, cabeceras, producto_prueba["id_producto"], producto_prueba["B"], 1)
    id_direccion = _direccion(cliente_http, cabeceras, complemento="Casa 4", codigo_postal="763021")
    return cabeceras, id_usuario, id_direccion


# ---------------------------------------------------------------------------
# Registro exitoso (RF-16 a RF-19)
# ---------------------------------------------------------------------------

def test_registro_completo(cliente_http, conn, carrito_listo, producto_prueba, variante_base):
    cabeceras, id_usuario, id_direccion = carrito_listo
    _agregar(cliente_http, cabeceras, variante_base["id_producto"], variante_base["id_variante"], 1)
    stock_base = conn.execute("SELECT stock FROM variante_producto WHERE id_variante = %s",
                              (variante_base["id_variante"],)).fetchone()["stock"]
    id_carrito = conn.execute("SELECT id_carrito FROM carrito WHERE id_usuario = %s AND estado = 'abierto'",
                              (id_usuario,)).fetchone()["id_carrito"]

    respuesta = _confirmar(cliente_http, cabeceras, id_direccion, observaciones="  Llamar antes  ")
    assert respuesta.status_code == 201, respuesta.get_json()
    pedido = respuesta.get_json()["pedido"]
    assert isinstance(pedido["id_pedido"], int) and pedido["estado"] == "pendiente"
    assert pedido["observaciones"] == "Llamar antes"
    assert pedido["entrega"] == {"id_direccion": id_direccion, **DIRECCION,
                                 "complemento": "Casa 4", "codigo_postal": "763021"}
    # 2 x 33333.33 + 1 x 33333.33 + 1 x 65000.00
    assert (pedido["subtotal"], pedido["total"]) == ("164999.99", "164999.99")
    # Las líneas se registran en orden ascendente de id_variante (orden de bloqueo).
    assert [(d["id_variante"], d["cantidad"], d["precio_unitario"], d["subtotal"]) for d in pedido["detalles"]] == sorted([
        (producto_prueba["A"], 2, "33333.33", "66666.66"),
        (producto_prueba["B"], 1, "33333.33", "33333.33"),
        (variante_base["id_variante"], 1, "65000.00", "65000.00"),
    ])
    base = next(d for d in pedido["detalles"] if d["id_variante"] == variante_base["id_variante"])
    assert (base["talla"], base["color"], base["compatibilidad"]) == (None, None, None)

    # Inventario descontado exactamente y movimientos coherentes.
    filas = conn.execute("SELECT id_variante, stock FROM variante_producto WHERE id_variante = ANY(%s)",
                         ([producto_prueba["A"], producto_prueba["B"], variante_base["id_variante"]],)).fetchall()
    stock = {f["id_variante"]: f["stock"] for f in filas}
    assert stock == {producto_prueba["A"]: 3, producto_prueba["B"]: 2, variante_base["id_variante"]: stock_base - 1}
    movimientos = conn.execute(
        "SELECT id_variante, id_usuario, tipo, cantidad, stock_anterior, stock_nuevo, motivo "
        "FROM movimiento_inventario WHERE id_pedido = %s ORDER BY id_variante", (pedido["id_pedido"],)).fetchall()
    assert [(m["id_variante"], m["tipo"], m["cantidad"], m["stock_anterior"], m["stock_nuevo"]) for m in movimientos] == sorted([
        (producto_prueba["A"], "salida", 2, 5, 3),
        (producto_prueba["B"], "salida", 1, 3, 2),
        (variante_base["id_variante"], "salida", 1, stock_base, stock_base - 1),
    ])
    assert all(m["id_usuario"] == id_usuario and str(pedido["id_pedido"]) in m["motivo"] for m in movimientos)

    # Fila del pedido y suma de líneas (columna generada) coherentes.
    fila = conn.execute("SELECT id_usuario, subtotal, total, estado, id_usuario_actualizacion FROM pedido "
                        "WHERE id_pedido = %s", (pedido["id_pedido"],)).fetchone()
    suma = conn.execute("SELECT sum(subtotal) AS s FROM detalle_pedido WHERE id_pedido = %s",
                        (pedido["id_pedido"],)).fetchone()["s"]
    assert fila == {"id_usuario": id_usuario, "subtotal": Decimal("164999.99"), "total": Decimal("164999.99"),
                    "estado": "pendiente", "id_usuario_actualizacion": None}
    assert suma == Decimal("164999.99")

    # Carrito convertido; el siguiente GET /carrito está vacío.
    assert conn.execute("SELECT estado FROM carrito WHERE id_carrito = %s", (id_carrito,)).fetchone()["estado"] == "convertido"
    assert cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]["id_carrito"] is None

    # RF-19: el detalle consultado coincide con la respuesta de creación.
    detalle = cliente_http.get(f"/api/pedidos/{pedido['id_pedido']}", headers=cabeceras)
    assert detalle.status_code == 200 and detalle.get_json()["pedido"] == pedido


def test_repetir_la_confirmacion_no_duplica(cliente_http, conn, carrito_listo, producto_prueba):
    cabeceras, id_usuario, id_direccion = carrito_listo
    assert _confirmar(cliente_http, cabeceras, id_direccion).status_code == 201
    antes = _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]])
    repetida = _confirmar(cliente_http, cabeceras, id_direccion)
    assert repetida.status_code == 409 and _codigo(repetida) == "carrito_vacio"
    assert _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]]) == antes


def test_nueva_compra_usa_un_carrito_nuevo(cliente_http, conn, carrito_listo, producto_prueba):
    cabeceras, id_usuario, id_direccion = carrito_listo
    primero = _confirmar(cliente_http, cabeceras, id_direccion).get_json()["pedido"]
    _agregar(cliente_http, cabeceras, producto_prueba["id_producto"], producto_prueba["A"], 1)
    segundo = _confirmar(cliente_http, cabeceras, id_direccion).get_json()["pedido"]
    assert segundo["id_pedido"] > primero["id_pedido"]
    carritos = conn.execute("SELECT estado FROM carrito WHERE id_usuario = %s ORDER BY id_carrito",
                            (id_usuario,)).fetchall()
    assert [c["estado"] for c in carritos] == ["convertido", "convertido"]


def test_historico_conserva_precio_direccion_y_productos_desactivados(cliente_http, conn, carrito_listo, producto_prueba):
    cabeceras, _, id_direccion = carrito_listo
    pedido = _confirmar(cliente_http, cabeceras, id_direccion).get_json()["pedido"]

    conn.execute("UPDATE producto SET precio = 99999.00 WHERE id_producto = %s", (producto_prueba["id_producto"],))
    cliente_http.patch(f"/api/direcciones/{id_direccion}", headers=cabeceras, json={"direccion": "Nueva 9 # 9-9"})
    cliente_http.delete(f"/api/direcciones/{id_direccion}", headers=cabeceras)
    conn.execute("UPDATE variante_producto SET activo = false WHERE id_variante = %s", (producto_prueba["B"],))
    conn.execute("UPDATE producto SET activo = false WHERE id_producto = %s", (producto_prueba["id_producto"],))

    consultado = cliente_http.get(f"/api/pedidos/{pedido['id_pedido']}", headers=cabeceras)
    assert consultado.status_code == 200
    consultado = consultado.get_json()["pedido"]
    assert consultado["detalles"][0]["precio_unitario"] == "33333.33"
    assert consultado["total"] == pedido["total"]
    assert consultado["entrega"]["direccion"] == DIRECCION["direccion"]
    assert len(consultado["detalles"]) == 2


# ---------------------------------------------------------------------------
# Errores de negocio: nada se registra
# ---------------------------------------------------------------------------

def test_sin_carrito_o_carrito_vacio(cliente_http, sesion, producto_prueba):
    cabeceras, _, _ = sesion
    id_direccion = _direccion(cliente_http, cabeceras)
    respuesta = _confirmar(cliente_http, cabeceras, id_direccion)
    assert respuesta.status_code == 409 and _codigo(respuesta) == "carrito_vacio"

    carrito = _agregar(cliente_http, cabeceras, producto_prueba["id_producto"], producto_prueba["A"], 1)
    cliente_http.delete(f"/api/carrito/items/{carrito['items'][0]['id_detalle_carrito']}", headers=cabeceras)
    respuesta = _confirmar(cliente_http, cabeceras, id_direccion)
    assert respuesta.status_code == 409 and _codigo(respuesta) == "carrito_vacio"


def test_direccion_inexistente_inactiva_o_ajena(cliente_http, conn, carrito_listo, nueva_sesion, producto_prueba):
    cabeceras, id_usuario, id_direccion = carrito_listo
    otro, _, _ = nueva_sesion()
    ajena = _direccion(cliente_http, otro)
    inactiva = _direccion(cliente_http, cabeceras, direccion="Vieja 1")
    cliente_http.delete(f"/api/direcciones/{inactiva}", headers=cabeceras)
    antes = _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]])
    for id_dir in (2_147_483_647, ajena, inactiva):
        respuesta = _confirmar(cliente_http, cabeceras, id_dir)
        assert respuesta.status_code == 404 and _codigo(respuesta) == "direccion_no_encontrada"
    assert _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]]) == antes


@pytest.mark.parametrize("cambio, motivo", [
    ("UPDATE variante_producto SET stock = 1 WHERE id_variante = {A}", "stock_insuficiente"),
    ("UPDATE variante_producto SET stock = 0 WHERE id_variante = {A}", "sin_stock"),
    ("UPDATE variante_producto SET activo = false WHERE id_variante = {A}", "variante_inactiva"),
    ("UPDATE producto SET activo = false WHERE id_producto = {P}", "producto_inactivo"),
    ("UPDATE categoria SET activo = false WHERE id_categoria = {C}", "categoria_inactiva"),
])
def test_articulos_no_disponibles(cliente_http, conn, carrito_listo, producto_prueba, cambio, motivo):
    cabeceras, id_usuario, id_direccion = carrito_listo
    conn.execute(cambio.format(A=producto_prueba["A"], P=producto_prueba["id_producto"],
                               C=producto_prueba["id_categoria"]))
    antes = _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]])
    respuesta = _confirmar(cliente_http, cabeceras, id_direccion)
    assert respuesta.status_code == 409 and _codigo(respuesta) == "articulos_no_disponibles"
    problemas = respuesta.get_json()["error"]["detalles"]["items"]
    assert any(p["id_variante"] == producto_prueba["A"] and p["motivo"] == motivo for p in problemas)
    assert _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]]) == antes


def test_pedido_ajeno_o_inexistente_404(cliente_http, carrito_listo, nueva_sesion):
    cabeceras, _, id_direccion = carrito_listo
    pedido = _confirmar(cliente_http, cabeceras, id_direccion).get_json()["pedido"]
    otro, _, _ = nueva_sesion()
    for headers, id_pedido in ((otro, pedido["id_pedido"]), (cabeceras, 2_147_483_647)):
        respuesta = cliente_http.get(f"/api/pedidos/{id_pedido}", headers=headers)
        assert respuesta.status_code == 404 and _codigo(respuesta) == "pedido_no_encontrado"


# ---------------------------------------------------------------------------
# Fallos a mitad de la transacción: reversión total
# ---------------------------------------------------------------------------

def _fallar_en_segunda_llamada(monkeypatch, clase, metodo, resultado=RuntimeError("fallo simulado")):
    original = getattr(clase, metodo)
    llamadas = {"n": 0}

    def envoltura(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            if isinstance(resultado, Exception):
                raise resultado
            return resultado
        return original(*args, **kwargs)

    monkeypatch.setattr(clase, metodo, staticmethod(envoltura))


@pytest.mark.parametrize("clase, metodo, resultado, http", [
    (PedidoDAO, "insertar_detalle", RuntimeError("fallo simulado"), 500),
    (InventarioDAO, "registrar_salida_por_pedido", RuntimeError("fallo simulado"), 500),
    (InventarioDAO, "registrar_salida_por_pedido", None, 409),   # stock tomado por otro
])
def test_fallo_intermedio_revierte_todo(monkeypatch, cliente_http, conn, carrito_listo, producto_prueba,
                                        clase, metodo, resultado, http):
    cabeceras, id_usuario, id_direccion = carrito_listo
    antes = _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]])
    _fallar_en_segunda_llamada(monkeypatch, clase, metodo, resultado)
    respuesta = _confirmar(cliente_http, cabeceras, id_direccion)
    assert respuesta.status_code == http
    assert "fallo simulado" not in respuesta.get_data(as_text=True)
    assert _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]]) == antes
    assert conn.execute("SELECT count(*) AS n FROM detalle_pedido d JOIN pedido p USING (id_pedido) "
                        "WHERE p.id_usuario = %s", (id_usuario,)).fetchone()["n"] == 0


def test_fallo_al_convertir_el_carrito_revierte_todo(monkeypatch, cliente_http, conn, carrito_listo, producto_prueba):
    cabeceras, id_usuario, id_direccion = carrito_listo
    antes = _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]])
    monkeypatch.setattr(CarritoDAO, "marcar_convertido", staticmethod(lambda *a, **k: False))
    assert _confirmar(cliente_http, cabeceras, id_direccion).status_code == 409
    assert _foto(conn, id_usuario, [producto_prueba["A"], producto_prueba["B"]]) == antes


# ---------------------------------------------------------------------------
# Concurrencia real
# ---------------------------------------------------------------------------

def _en_paralelo(app_bd, solicitudes):
    """Ejecuta solicitudes POST /api/pedidos a la vez; devuelve los códigos HTTP."""
    barrera = threading.Barrier(len(solicitudes))
    resultados = [None] * len(solicitudes)

    def ejecutar(i, cabeceras, id_direccion):
        cliente = app_bd.test_client()
        barrera.wait()
        resultados[i] = cliente.post("/api/pedidos", headers=cabeceras, json={"id_direccion": id_direccion})

    hilos = [threading.Thread(target=ejecutar, args=(i, *s)) for i, s in enumerate(solicitudes)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
    return resultados


def test_dos_solicitudes_simultaneas_mismo_carrito(app_bd, conn, carrito_listo, producto_prueba):
    cabeceras, id_usuario, id_direccion = carrito_listo
    resultados = _en_paralelo(app_bd, [(cabeceras, id_direccion)] * 2)
    codigos = sorted(r.status_code for r in resultados)
    assert codigos == [201, 409]
    assert conn.execute("SELECT count(*) AS n FROM pedido WHERE id_usuario = %s", (id_usuario,)).fetchone()["n"] == 1
    movimientos = conn.execute("SELECT id_variante, count(*) AS n FROM movimiento_inventario "
                               "WHERE id_variante = ANY(%s) GROUP BY id_variante",
                               ([producto_prueba["A"], producto_prueba["B"]],)).fetchall()
    assert sorted(m["n"] for m in movimientos) == [1, 1]
    stock = {f["id_variante"]: f["stock"] for f in conn.execute(
        "SELECT id_variante, stock FROM variante_producto WHERE id_variante = ANY(%s)",
        ([producto_prueba["A"], producto_prueba["B"]],)).fetchall()}
    assert stock == {producto_prueba["A"]: 3, producto_prueba["B"]: 2}


def test_dos_clientes_compiten_por_las_ultimas_unidades(app_bd, cliente_http, conn, nueva_sesion, producto_prueba):
    # Variante B tiene 3 unidades; cada cliente quiere 2 (el carrito lo permite a ambos).
    sesiones = []
    for _ in range(2):
        cabeceras, id_usuario, _ = nueva_sesion()
        _agregar(cliente_http, cabeceras, producto_prueba["id_producto"], producto_prueba["B"], 2)
        sesiones.append((cabeceras, _direccion(cliente_http, cabeceras), id_usuario))

    resultados = _en_paralelo(app_bd, [(c, d) for c, d, _ in sesiones])
    assert sorted(r.status_code for r in resultados) == [201, 409]
    perdedor = next(r for r in resultados if r.status_code == 409).get_json()["error"]
    assert perdedor["codigo"] == "articulos_no_disponibles"
    assert perdedor["detalles"]["items"][0]["stock_disponible"] == 1

    assert conn.execute("SELECT stock FROM variante_producto WHERE id_variante = %s",
                        (producto_prueba["B"],)).fetchone()["stock"] == 1
    salidas = conn.execute("SELECT stock_anterior, stock_nuevo FROM movimiento_inventario "
                           "WHERE id_variante = %s", (producto_prueba["B"],)).fetchall()
    assert [(s["stock_anterior"], s["stock_nuevo"]) for s in salidas] == [(3, 1)]
