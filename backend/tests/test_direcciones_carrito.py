"""Pruebas unitarias de direcciones (RF-11) y carrito (RF-12 a RF-15).

Sin base de datos: cubren autenticación, roles, validación de entrada (que
ocurre antes de abrir una conexión) y los cálculos del modelo Carrito. Las
reglas que dependen de datos (propiedad, stock, estados, reactivación) se
prueban contra PostgreSQL real en tests/integracion/test_bd_direcciones_carrito.py.
"""
from decimal import Decimal

import pytest

from models.carrito import Carrito, ItemCarrito

RUTAS_PROTEGIDAS = [
    ("get", "/api/direcciones"), ("post", "/api/direcciones"), ("get", "/api/direcciones/1"),
    ("patch", "/api/direcciones/1"), ("delete", "/api/direcciones/1"),
    ("get", "/api/carrito"), ("post", "/api/carrito/items"),
    ("patch", "/api/carrito/items/1"), ("delete", "/api/carrito/items/1"),
    ("patch", "/api/perfil"),
]


@pytest.mark.parametrize("metodo, ruta", RUTAS_PROTEGIDAS)
def test_sin_token_401(client, metodo, ruta):
    respuesta = getattr(client, metodo)(ruta, json={})
    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"]["codigo"] == "no_autenticado"


@pytest.mark.parametrize("metodo, ruta", RUTAS_PROTEGIDAS)
def test_empleado_sin_permiso_403(client, cabeceras, metodo, ruta):
    respuesta = getattr(client, metodo)(ruta, json={}, headers=cabeceras["empleado"])
    assert respuesta.status_code == 403


DIRECCION = {"departamento": "Valle del Cauca", "municipio": "Tuluá", "direccion": "Calle 26 # 30-15"}


@pytest.mark.parametrize(
    "cuerpo, campo",
    [
        ({**DIRECCION, "departamento": " "}, "departamento"),
        ({**DIRECCION, "municipio": None}, "municipio"),
        ({k: v for k, v in DIRECCION.items() if k != "direccion"}, "direccion"),
        ({**DIRECCION, "direccion": "x" * 151}, "direccion"),
        ({**DIRECCION, "complemento": "x" * 101}, "complemento"),
        ({**DIRECCION, "codigo_postal": "76A"}, "codigo_postal"),
        ({**DIRECCION, "codigo_postal": "123"}, "codigo_postal"),
        ({**DIRECCION, "principal": "si"}, "principal"),
        ({**DIRECCION, "departamento": 5}, "departamento"),
    ],
)
def test_direccion_campos_invalidos(client, cabeceras, cuerpo, campo):
    respuesta = client.post("/api/direcciones", json=cuerpo, headers=cabeceras["cliente"])
    assert respuesta.status_code == 400
    assert campo in respuesta.get_json()["error"]["detalles"]["campos"]


@pytest.mark.parametrize("campo", ["id_usuario", "activo", "id_direccion"])
def test_direccion_no_acepta_propietario_ni_estado(client, cabeceras, campo):
    respuesta = client.post("/api/direcciones", json={**DIRECCION, campo: 99}, headers=cabeceras["cliente"])
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["codigo"] == "campo_no_permitido"


def test_direccion_patch_vacio_400(client, cabeceras):
    assert client.patch("/api/direcciones/1", json={}, headers=cabeceras["cliente"]).status_code == 400


@pytest.mark.parametrize(
    "cuerpo, campo",
    [
        ({"id_producto": 1, "id_variante": 1, "cantidad": 0}, "cantidad"),
        ({"id_producto": 1, "id_variante": 1, "cantidad": -2}, "cantidad"),
        ({"id_producto": 1, "id_variante": 1, "cantidad": 1.5}, "cantidad"),
        ({"id_producto": 1, "id_variante": 1, "cantidad": "2"}, "cantidad"),
        ({"id_producto": 1, "id_variante": 1, "cantidad": True}, "cantidad"),
        ({"id_producto": 1, "cantidad": 1}, "id_variante"),
        ({"id_variante": 1, "cantidad": 1}, "id_producto"),
        ({"id_producto": 1, "id_variante": 1}, "cantidad"),
    ],
)
def test_agregar_datos_invalidos(client, cabeceras, cuerpo, campo):
    respuesta = client.post("/api/carrito/items", json=cuerpo, headers=cabeceras["cliente"])
    assert respuesta.status_code == 400
    assert campo in respuesta.get_json()["error"]["detalles"]["campos"]


@pytest.mark.parametrize("campo", ["precio", "precio_unitario", "subtotal", "id_carrito"])
def test_agregar_rechaza_precios_del_frontend(client, cabeceras, campo):
    cuerpo = {"id_producto": 1, "id_variante": 1, "cantidad": 1, campo: "1.00"}
    respuesta = client.post("/api/carrito/items", json=cuerpo, headers=cabeceras["cliente"])
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"]["codigo"] == "campo_no_permitido"


@pytest.mark.parametrize("cuerpo", [{"cantidad": 0}, {"cantidad": "3"}, {}, {"cantidad": 2, "precio": 1}])
def test_modificar_cantidad_invalida(client, cabeceras, cuerpo):
    assert client.patch("/api/carrito/items/1", json=cuerpo, headers=cabeceras["cliente"]).status_code == 400


def _item(**cambios):
    datos = dict(id_detalle_carrito=1, id_carrito=1, id_producto=1, id_variante=1, cantidad=3,
                 nombre="Casco", referencia="CAS-1", precio=Decimal("33333.33"), stock=5)
    datos.update(cambios)
    return ItemCarrito(**datos)


def test_importes_con_decimal():
    carrito = Carrito(id_carrito=1, items=[_item(), _item(id_detalle_carrito=2, cantidad=1, precio=Decimal("0.10"))])
    datos = carrito.to_dict()
    assert datos["items"][0]["precio_unitario"] == "33333.33"
    assert datos["items"][0]["subtotal"] == "99999.99"
    assert datos["total"] == "100000.09"
    assert (datos["cantidad_items"], datos["cantidad_unidades"]) == (2, 4)


def test_carrito_vacio():
    assert Carrito().to_dict() == {
        "id_carrito": None, "estado": "abierto", "items": [], "cantidad_items": 0,
        "cantidad_unidades": 0, "total": "0.00", "vacio": True, "todos_disponibles": True,
    }


@pytest.mark.parametrize(
    "cambios, motivo, stock_visible",
    [
        ({}, None, 5),
        ({"cantidad": 5}, None, 5),
        ({"cantidad": 6}, "stock_insuficiente", 5),
        ({"stock": 0}, "sin_stock", 0),
        ({"producto_activo": False}, "producto_inactivo", 0),
        ({"categoria_activa": False}, "categoria_inactiva", 0),
        ({"variante_activa": False}, "variante_inactiva", 0),
    ],
)
def test_disponibilidad_de_items(cambios, motivo, stock_visible):
    item = _item(**cambios).to_dict()
    assert item["motivo_no_disponible"] == motivo
    assert item["disponible"] is (motivo is None)
    assert item["stock_disponible"] == stock_visible


def test_item_no_disponible_sigue_en_el_total():
    carrito = Carrito(id_carrito=1, items=[_item(producto_activo=False)])
    assert carrito.to_dict()["total"] == "99999.99"
    assert carrito.to_dict()["todos_disponibles"] is False
