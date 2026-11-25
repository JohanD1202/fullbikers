# Consultas SQL del catálogo y página principal
from config.database import get_db_connection
from models.producto import Categoria, Producto, VarianteProducto

class ProductoDAO:
    @staticmethod
    def obtener_categorias_activas():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id_categoria, nombre, descripcion, estado
                    FROM categoria
                    WHERE estado = TRUE
                    ORDER BY nombre ASC;
                    """
                )
                filas = cur.fetchall()
                return [
                    Categoria(
                        id_categoria=f["id_categoria"],
                        nombre=f["nombre"],
                        descripcion=f["descripcion"],
                        estado=f["estado"]
                    ).to_dict()
                    for f in filas
                ]
        finally:
            conn.close()

    @staticmethod
    def listar_catalogo(id_categoria=None, busqueda=None):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        p.id_producto,
                        p.id_categoria,
                        c.nombre AS categoria_nombre,
                        p.nombre,
                        p.referencia,
                        p.descripcion,
                        p.marca,
                        p.precio,
                        p.imagen,
                        p.estado,
                        COALESCE(SUM(vp.stock), 0) AS stock_total
                    FROM producto p
                    INNER JOIN categoria c ON p.id_categoria = c.id_categoria
                    LEFT JOIN variante_producto vp ON p.id_producto = vp.id_producto
                    WHERE p.estado = TRUE AND c.estado = TRUE
                """
                params = []

                if id_categoria:
                    query += " AND p.id_categoria = %s"
                    params.append(id_categoria)

                if busqueda:
                    termino = f"%{busqueda.strip()}%"
                    query += " AND (p.nombre ILIKE %s OR p.referencia ILIKE %s)"
                    params.extend([termino, termino])

                query += """
                    GROUP BY p.id_producto, c.nombre
                    ORDER BY p.id_producto DESC;
                """

                cur.execute(query, tuple(params))
                filas = cur.fetchall()

                return [
                    Producto(
                        id_producto=f["id_producto"],
                        id_categoria=f["id_categoria"],
                        categoria_nombre=f["categoria_nombre"],
                        nombre=f["nombre"],
                        referencia=f["referencia"],
                        descripcion=f["descripcion"],
                        marca=f["marca"],
                        precio=f["precio"],
                        imagen=f["imagen"],
                        estado=f["estado"],
                        stock_total=f["stock_total"]
                    ).to_dict()
                    for f in filas
                ]
        finally:
            conn.close()

    @staticmethod
    def obtener_detalle_producto(id_producto: int):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        p.id_producto,
                        p.id_categoria,
                        c.nombre AS categoria_nombre,
                        p.nombre,
                        p.referencia,
                        p.descripcion,
                        p.marca,
                        p.precio,
                        p.imagen,
                        p.estado
                    FROM producto p
                    INNER JOIN categoria c ON p.id_categoria = c.id_categoria
                    WHERE p.id_producto = %s AND p.estado = TRUE AND c.estado = TRUE;
                    """,
                    (id_producto,)
                )
                fila_prod = cur.fetchone()
                if not fila_prod:
                    return None

                cur.execute(
                    """
                    SELECT id_variante, id_producto, talla, color, compatibilidad, sku, stock
                    FROM variante_producto
                    WHERE id_producto = %s
                    ORDER BY id_variante ASC;
                    """,
                    (id_producto,)
                )
                filas_var = cur.fetchall()

                variantes = [
                    VarianteProducto(
                        id_variante=v["id_variante"],
                        id_producto=v["id_producto"],
                        sku=v["sku"],
                        stock=v["stock"],
                        talla=v["talla"],
                        color=v["color"],
                        compatibilidad=v["compatibilidad"]
                    )
                    for v in filas_var
                ]

                stock_total = sum(v.stock for v in variantes)
                producto = Producto(
                    id_producto=fila_prod["id_producto"],
                    id_categoria=fila_prod["id_categoria"],
                    categoria_nombre=fila_prod["categoria_nombre"],
                    nombre=fila_prod["nombre"],
                    referencia=fila_prod["referencia"],
                    descripcion=fila_prod["descripcion"],
                    marca=fila_prod["marca"],
                    precio=fila_prod["precio"],
                    imagen=fila_prod["imagen"],
                    estado=fila_prod["estado"],
                    stock_total=stock_total,
                    variantes=variantes
                )
                return producto.to_dict(incluir_variantes=True)
        finally:
            conn.close()