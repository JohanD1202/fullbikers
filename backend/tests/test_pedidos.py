"""Pruebas unitarias de pedidos (RF-16 a RF-19) sin base de datos.

Cubren autenticación, roles, validación de la solicitud (ocurre antes de abrir
la transacción) y la serialización del modelo. La transacción, el inventario y
la concurrencia se prueban contra PostgreSQL real en
tests/integracion/test_bd_pedidos.py.
"""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from models.carrito import ItemCarrito
from models.pedido import DetallePedido, Pedido
from services import pedido_service


@pytest.mark.parametrize("metodo, ruta", [("post", "/api/pedidos"), ("get", "/api/pedidos/1")])
def test_sin_token_401(client, metodo, ruta):
    assert getattr(client, metodo)(ruta, json={"id_direccion": 1}).status_code == 401


@pytest.mark.parametrize("metodo, ruta", [("post", "/api/pedidos"), ("get", "/api/pedidos/1")])
def test_empleado_403(client, cabeceras, metodo, ruta):
    assert getattr(client, metodo)(ruta, json={"id_direccion": 1}, headers=cabeceras["empleado"]).status_code == 403


@pytest.mark.parametrize(
    "campo",
    ["id_usuario", "precio_unitario", "subtotal", "total", "estado", "stock", "id_pedido", "items", "id_carrito"],
)
def test_campos_no_permitidos(client, cabeceras, campo):
    respuesta = client.post("/api/pedidos", json={"id_direccion": 1, campo: 1}, headers=cabeceras["cliente"])
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["codigo"] == "campo_no_permitido"


@pytest.mark.parametrize(
    "cuerpo, campo",
    [
        ({}, "id_direccion"),
        ({"id_direccion": "1"}, "id_direccion"),
        ({"id_direccion": 0}, "id_direccion"),
        ({"id_direccion": True}, "id_direccion"),
        ({"id_direccion": 1, "observaciones": "x" * 1001}, "observaciones"),
        ({"id_direccion": 1, "observaciones": 5}, "observaciones"),
    ],
)
def test_solicitud_invalida(client, cabeceras, cuerpo, campo):
    respuesta = client.post("/api/pedidos", json=cuerpo, headers=cabeceras["cliente"])
    assert respuesta.status_code == 400
    assert campo in respuesta.get_json()["error"]["detalles"]["campos"]


def test_cuerpo_no_json(client, cabeceras):
    respuesta = client.post("/api/pedidos", data="x", content_type="application/json", headers=cabeceras["cliente"])
    assert respuesta.get_json()["error"]["codigo"] == "solicitud_invalida"


def test_observaciones_vacias_son_none():
    assert pedido_service._validar_solicitud({"id_direccion": 3, "observaciones": "  "}) == (3, None)
    assert pedido_service._validar_solicitud({"id_direccion": 3, "observaciones": " Timbre 2 "}) == (3, "Timbre 2")


def _item(**cambios):
    datos = dict(id_detalle_carrito=1, id_carrito=1, id_producto=1, id_variante=1, cantidad=2,
                 nombre="Casco", referencia="CAS-1", precio=Decimal("10.00"), stock=5)
    datos.update(cambios)
    return ItemCarrito(**datos)


def test_disponibilidad_informa_todos_los_problemas():
    items = [_item(), _item(id_detalle_carrito=2, id_variante=2, cantidad=6),
             _item(id_detalle_carrito=3, id_variante=3, producto_activo=False)]
    with pytest.raises(Exception) as error:
        pedido_service._exigir_disponibilidad(items)
    assert error.value.codigo == "articulos_no_disponibles"
    problemas = error.value.detalles["items"]
    assert [(p["id_variante"], p["motivo"], p["stock_disponible"]) for p in problemas] == [
        (2, "stock_insuficiente", 5), (3, "producto_inactivo", 0)]


def test_disponibilidad_correcta_no_lanza():
    pedido_service._exigir_disponibilidad([_item(), _item(id_variante=2, cantidad=5)])


def test_serializacion_del_pedido():
    fecha = datetime(2026, 11, 26, 15, 30, tzinfo=timezone.utc)
    detalle = DetallePedido(1, 4, 9, 3, Decimal("33333.33"), Decimal("99999.99"), nombre="Casco", talla="M")
    pedido = Pedido(id_pedido=15, id_usuario=7, id_direccion=2, fecha=fecha, estado="pendiente",
                    subtotal=Decimal("99999.99"), total=Decimal("99999.99"),
                    departamento_entrega="Valle del Cauca", municipio_entrega="Tuluá",
                    direccion_entrega="Calle 1", observaciones=None, fecha_actualizacion=fecha,
                    detalles=[detalle])
    datos = pedido.to_dict()
    assert datos["id_pedido"] == 15 and datos["estado"] == "pendiente"
    assert datos["fecha"] == "2026-11-26T15:30:00+00:00"
    assert datos["entrega"]["municipio"] == "Tuluá"
    assert datos["detalles"][0]["precio_unitario"] == "33333.33"
    assert datos["detalles"][0]["subtotal"] == "99999.99"
    assert (datos["subtotal"], datos["total"], datos["cantidad_unidades"]) == ("99999.99", "99999.99", 3)
    assert "id_usuario" not in datos
