# Clases de dominio: Categoria, Producto,
class Categoria:
    def __init__(self, id_categoria, nombre, descripcion=None, estado=True):
        self.id_categoria = id_categoria
        self.nombre = nombre
        self.descripcion = descripcion
        self.estado = estado

    def to_dict(self):
        return {
            "id_categoria": self.id_categoria,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "estado": self.estado
        }


class VarianteProducto:
    def __init__(self, id_variante, id_producto, sku, stock=0, talla=None, color=None, compatibilidad=None):
        self.id_variante = id_variante
        self.id_producto = id_producto
        self.talla = talla
        self.color = color
        self.compatibilidad = compatibilidad
        self.sku = sku
        self.stock = int(stock)

    def to_dict(self):
        return {
            "id_variante": self.id_variante,
            "id_producto": self.id_producto,
            "talla": self.talla,
            "color": self.color,
            "compatibilidad": self.compatibilidad,
            "sku": self.sku,
            "stock": self.stock,
            "disponible": self.stock > 0
        }


class Producto:
    def __init__(self, id_producto, id_categoria, nombre, referencia, precio, descripcion=None, marca=None, imagen=None, estado=True, categoria_nombre=None, stock_total=0, variantes=None):
        self.id_producto = id_producto
        self.id_categoria = id_categoria
        self.categoria_nombre = categoria_nombre
        self.nombre = nombre
        self.referencia = referencia
        self.descripcion = descripcion
        self.marca = marca
        self.precio = float(precio)
        self.imagen = imagen
        self.estado = estado
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
            "precio": self.precio,
            "imagen": self.imagen,
            "stock_total": self.stock_total,
            "disponible": self.stock_total > 0
        }
        if incluir_variantes:
            data["variantes"] = [v.to_dict() for v in self.variantes]
        return data