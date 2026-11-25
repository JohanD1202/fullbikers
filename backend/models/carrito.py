# Clases de dominio del carrito: ItemCarrito (detalle_carrito + datos vigentes
# de producto, categoría y variante) y Carrito.
#
# Precios: siempre el precio VIGENTE de producto.precio (el carrito no guarda
# precios). Importes con Decimal y serializados como "123456.00" (models/dinero).
from decimal import Decimal

from models.dinero import a_decimal, serializar_dinero

ABIERTO = "abierto"
CONVERTIDO = "convertido"
ABANDONADO = "abandonado"

# Motivos por los que un artículo del carrito no puede comprarse ahora.
PRODUCTO_INACTIVO = "producto_inactivo"
CATEGORIA_INACTIVA = "categoria_inactiva"
VARIANTE_INACTIVA = "variante_inactiva"
SIN_STOCK = "sin_stock"
STOCK_INSUFICIENTE = "stock_insuficiente"


class ItemCarrito:
    def __init__(self, id_detalle_carrito, id_carrito, id_producto, id_variante, cantidad,
                 nombre, referencia, precio, stock, producto_activo=True, categoria_activa=True,
                 variante_activa=True, imagen=None, marca=None, categoria=None, sku=None,
                 talla=None, color=None, compatibilidad=None):
        self.id_detalle_carrito = id_detalle_carrito
        self.id_carrito = id_carrito
        self.id_producto = id_producto
        self.id_variante = id_variante
        self.cantidad = int(cantidad)
        self.nombre = nombre
        self.referencia = referencia
        self.imagen = imagen
        self.marca = marca
        self.categoria = categoria
        self.sku = sku
        self.talla = talla
        self.color = color
        self.compatibilidad = compatibilidad
        self.precio = a_decimal(precio)
        self.stock = int(stock)
        self.producto_activo = producto_activo
        self.categoria_activa = categoria_activa
        self.variante_activa = variante_activa

    @classmethod
    def desde_fila(cls, fila):
        return cls(**fila)

    @property
    def subtotal(self):
        return a_decimal(self.precio * self.cantidad)

    @property
    def motivo_no_disponible(self):
        """None si se puede comprar la cantidad indicada; si no, el motivo."""
        if not self.producto_activo:
            return PRODUCTO_INACTIVO
        if not self.categoria_activa:
            return CATEGORIA_INACTIVA
        if not self.variante_activa:
            return VARIANTE_INACTIVA
        if self.stock <= 0:
            return SIN_STOCK
        if self.cantidad > self.stock:
            return STOCK_INSUFICIENTE
        return None

    @property
    def disponible(self):
        return self.motivo_no_disponible is None

    def to_dict(self):
        return {
            "id_detalle_carrito": self.id_detalle_carrito,
            "id_producto": self.id_producto,
            "id_variante": self.id_variante,
            "nombre": self.nombre,
            "referencia": self.referencia,
            "marca": self.marca,
            "categoria": self.categoria,
            "imagen": self.imagen,
            "sku": self.sku,
            "talla": self.talla,
            "color": self.color,
            "compatibilidad": self.compatibilidad,
            "cantidad": self.cantidad,
            "precio_unitario": serializar_dinero(self.precio),
            "subtotal": serializar_dinero(self.subtotal),
            "stock_disponible": self.stock if self.producto_activo and self.categoria_activa and self.variante_activa else 0,
            "disponible": self.disponible,
            "motivo_no_disponible": self.motivo_no_disponible,
        }


class Carrito:
    def __init__(self, id_carrito=None, estado=ABIERTO, fecha_creacion=None, items=None):
        self.id_carrito = id_carrito  # None: el usuario aún no tiene carrito abierto
        self.estado = estado
        self.fecha_creacion = fecha_creacion
        self.items = items or []

    @property
    def total(self):
        return a_decimal(sum((item.subtotal for item in self.items), Decimal("0")))

    def to_dict(self):
        return {
            "id_carrito": self.id_carrito,
            "estado": self.estado,
            "items": [item.to_dict() for item in self.items],
            "cantidad_items": len(self.items),
            "cantidad_unidades": sum(item.cantidad for item in self.items),
            "total": serializar_dinero(self.total),
            "vacio": not self.items,
            "todos_disponibles": all(item.disponible for item in self.items),
        }
