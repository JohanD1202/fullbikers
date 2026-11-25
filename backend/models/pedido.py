# Clases de dominio Pedido y DetallePedido (tablas pedido y detalle_pedido).
#
# Los importes son HISTÓRICOS: precio_unitario y subtotal se copian al
# registrar el pedido y no cambian si después cambia el precio del producto.
# Nombre, referencia y características se leen del producto y la variante
# ACTUALES (el esquema no guarda una copia; ver backend/API.md §9).
from models.dinero import a_decimal, serializar_dinero

PENDIENTE = "pendiente"
ESTADOS = ("pendiente", "confirmado", "en_preparacion", "enviado", "entregado", "cancelado")


def _iso(fecha):
    return fecha.isoformat() if fecha is not None else None


class DetallePedido:
    def __init__(self, id_detalle, id_producto, id_variante, cantidad, precio_unitario, subtotal,
                 nombre=None, referencia=None, imagen=None, sku=None, talla=None, color=None,
                 compatibilidad=None):
        self.id_detalle = id_detalle
        self.id_producto = id_producto
        self.id_variante = id_variante
        self.cantidad = int(cantidad)
        self.precio_unitario = a_decimal(precio_unitario)
        self.subtotal = a_decimal(subtotal)
        self.nombre = nombre
        self.referencia = referencia
        self.imagen = imagen
        self.sku = sku
        self.talla = talla
        self.color = color
        self.compatibilidad = compatibilidad

    @classmethod
    def desde_fila(cls, fila):
        return cls(**fila)

    def to_dict(self):
        return {
            "id_detalle": self.id_detalle,
            "id_producto": self.id_producto,
            "id_variante": self.id_variante,
            "nombre": self.nombre,
            "referencia": self.referencia,
            "imagen": self.imagen,
            "sku": self.sku,
            "talla": self.talla,
            "color": self.color,
            "compatibilidad": self.compatibilidad,
            "cantidad": self.cantidad,
            "precio_unitario": serializar_dinero(self.precio_unitario),
            "subtotal": serializar_dinero(self.subtotal),
        }


class Pedido:
    def __init__(self, id_pedido, id_usuario, id_direccion, fecha, estado, subtotal, total,
                 departamento_entrega, municipio_entrega, direccion_entrega,
                 complemento_entrega=None, codigo_postal_entrega=None, observaciones=None,
                 fecha_actualizacion=None, detalles=None, **_otros):
        self.id_pedido = id_pedido
        self.id_usuario = id_usuario
        self.id_direccion = id_direccion
        self.fecha = fecha
        self.estado = estado
        self.subtotal = a_decimal(subtotal)
        self.total = a_decimal(total)
        self.observaciones = observaciones
        self.departamento_entrega = departamento_entrega
        self.municipio_entrega = municipio_entrega
        self.direccion_entrega = direccion_entrega
        self.complemento_entrega = complemento_entrega
        self.codigo_postal_entrega = codigo_postal_entrega
        self.fecha_actualizacion = fecha_actualizacion
        self.detalles = detalles or []

    @classmethod
    def desde_fila(cls, fila, detalles=None):
        return cls(**fila, detalles=detalles)

    def to_dict(self):
        return {
            "id_pedido": self.id_pedido,
            "fecha": _iso(self.fecha),
            "estado": self.estado,
            "fecha_actualizacion": _iso(self.fecha_actualizacion),
            "entrega": {
                "id_direccion": self.id_direccion,
                "departamento": self.departamento_entrega,
                "municipio": self.municipio_entrega,
                "direccion": self.direccion_entrega,
                "complemento": self.complemento_entrega,
                "codigo_postal": self.codigo_postal_entrega,
            },
            "observaciones": self.observaciones,
            "detalles": [d.to_dict() for d in self.detalles],
            "cantidad_unidades": sum(d.cantidad for d in self.detalles),
            "subtotal": serializar_dinero(self.subtotal),
            "total": serializar_dinero(self.total),
        }
