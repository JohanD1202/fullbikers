# Clases de dominio del catálogo: Categoria, VarianteProducto y Producto.
# Los nombres de atributos siguen las columnas de database/schema.sql.
from models.dinero import a_decimal, serializar_dinero


class Categoria:
    def __init__(self, id_categoria, nombre, descripcion=None, activo=True):
        self.id_categoria = id_categoria
        self.nombre = nombre
        self.descripcion = descripcion
        self.activo = activo

    def to_dict(self):
        return {
            "id_categoria": self.id_categoria,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "activo": self.activo
        }


class VarianteProducto:
    def __init__(self, id_variante, id_producto, sku, stock=0, talla=None, color=None, compatibilidad=None, activo=True):
        self.id_variante = id_variante
        self.id_producto = id_producto
        self.talla = talla
        self.color = color
        self.compatibilidad = compatibilidad
        self.sku = sku
        self.stock = int(stock)
        self.activo = activo

    def to_dict(self):
        return {
            "id_variante": self.id_variante,
            "id_producto": self.id_producto,
            "talla": self.talla,
            "color": self.color,
            "compatibilidad": self.compatibilidad,
            "sku": self.sku,
            "stock": self.stock,
            # Una variante inactiva nunca está disponible para la venta.
            "disponible": self.activo and self.stock > 0
        }


class Producto:
    def __init__(self, id_producto, id_categoria, nombre, referencia, precio, descripcion=None, marca=None, imagen=None, activo=True, categoria_nombre=None, stock_total=0, variantes=None):
        self.id_producto = id_producto
        self.id_categoria = id_categoria
        self.categoria_nombre = categoria_nombre
        self.nombre = nombre
        self.referencia = referencia
        self.descripcion = descripcion
        self.marca = marca
        self.precio = a_decimal(precio)
        self.imagen = imagen
        self.activo = activo
        self.stock_total = int(stock_total)
        self.variantes = variantes or []

    def to_dict(self, incluir_variantes=False):
        data = {
            "id_producto": self.id_producto,
            "id_categoria": self.id_categoria,
            "categoria": self.categoria_nombre,
            "nombre": self.nombre,
            "referencia": self.referencia,
            "descripcion": self.descripcion,
            "marca": self.marca,
            "precio": serializar_dinero(self.precio),
            "imagen": self.imagen,
            "stock_total": self.stock_total,
            "disponible": self.stock_total > 0
        }
        if incluir_variantes:
            data["variantes"] = [v.to_dict() for v in self.variantes]
        return data