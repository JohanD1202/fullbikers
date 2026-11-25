from decimal import Decimal

import pytest

from models.dinero import a_decimal, serializar_dinero
from models.producto import Producto


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (Decimal("185000.00"), "185000.00"),
        (Decimal("185000"), "185000.00"),
        (185000, "185000.00"),
        ("99.995", "100.00"),
        (Decimal("1E+5"), "100000.00"),
        (Decimal("999999999999.99"), "999999999999.99"),
    ],
)
def test_serializacion_monetaria(valor, esperado):
    assert serializar_dinero(valor) == esperado


@pytest.mark.parametrize("valor", [0.1, None, "abc", Decimal("NaN"), Decimal("Infinity")])
def test_valores_monetarios_invalidos(valor):
    with pytest.raises((TypeError, ValueError)):
        a_decimal(valor)


def test_producto_conserva_decimal_internamente():
    producto = Producto(id_producto=1, id_categoria=1, nombre="X", referencia="X", precio=Decimal("10.50"))
    assert producto.precio == Decimal("10.50")
    assert producto.to_dict()["precio"] == "10.50"
