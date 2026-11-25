# Consultas SQL del catálogo y página principal.
#
# Reglas de la capa DAO (ver config/database.py):
#   * Cada método recibe la conexión como primer argumento; no abre, cierra,
#     confirma ni revierte transacciones.
#   * Solo SQL parametrizado (%s); nunca se concatena texto del usuario.
#
# Visibilidad del catálogo (database/README.md §6, §9 y consulta C1):
#   producto activo + categoría activa + al menos una variante activa.
#   El stock y la disponibilidad se calculan solo con variantes activas.
from models.producto import Categoria, Producto, VarianteProducto

# Tablas y condiciones comunes a la consulta y al conteo del catálogo.
_FROM_CATALOGO = """
    FROM producto p
    JOIN categoria c          ON c.id_categoria = p.id_categoria
    JOIN variante_producto vp ON vp.id_producto = p.id_producto AND vp.activo
    WHERE p.activo AND c.activo
"""


def escapar_patron_like(texto):
    """Escapa \\, % y _ para que se busquen literalmente en ILIKE."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtros_catalogo(id_categoria, busqueda):
    condiciones = ""
    params = []
    if id_categoria is not None:
        condiciones += " AND p.id_categoria = %s"
        params.append(id_categoria)
    if busqueda:
        # Búsqueda "contiene", sin distinguir mayúsculas, por nombre o referencia.
        termino = f"%{escapar_patron_like(busqueda)}%"
        condiciones += " AND (p.nombre ILIKE %s ESCAPE '\\' OR p.referencia ILIKE %s ESCAPE '\\')"
        params.extend([termino, termino])
    return condiciones, params


class ProductoDAO:
    @staticmethod
    def obtener_categorias_activas(conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id_categoria, nombre, descripcion, activo
                FROM categoria
                WHERE activo
                ORDER BY nombre ASC;
                """
            )
            filas = cur.fetchall()
        return [
            Categoria(
                id_categoria=f["id_categoria"],
                nombre=f["nombre"],
                descripcion=f["descripcion"],
                activo=f["activo"]
            ).to_dict()
            for f in filas
        ]

    @staticmethod
    def contar_catalogo(conn, id_categoria=None, busqueda=None):
        condiciones, params = _filtros_catalogo(id_categoria, busqueda)
        query = "SELECT COUNT(DISTINCT p.id_producto) AS total" + _FROM_CATALOGO + condiciones + ";"
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchone()["total"]

    @staticmethod
    def listar_catalogo(conn, id_categoria=None, busqueda=None, limite=None, desplazamiento=0):
        condiciones, params = _filtros_catalogo(id_categoria, busqueda)
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
                p.activo,
                SUM(vp.stock) AS stock_total
        """ + _FROM_CATALOGO + condiciones + """
            GROUP BY p.id_producto, c.nombre
            ORDER BY p.id_producto DESC
        """
        if limite is not None:
            query += " LIMIT %s OFFSET %s"
            params.extend([limite, desplazamiento])

        with conn.cursor() as cur:
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
                activo=f["activo"],
                stock_total=f["stock_total"]
            ).to_dict()
            for f in filas
        ]

    @staticmethod
    def obtener_detalle_producto(conn, id_producto: int):
        """Detalle con variantes activas, o None si el producto no es visible."""
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
                    p.activo
                FROM producto p
                JOIN categoria c ON c.id_categoria = p.id_categoria
                WHERE p.id_producto = %s AND p.activo AND c.activo;
                """,
                (id_producto,)
            )
            fila_prod = cur.fetchone()
            if not fila_prod:
                return None

            cur.execute(
                """
                SELECT id_variante, id_producto, talla, color, compatibilidad, sku, stock, activo
                FROM variante_producto
                WHERE id_producto = %s AND activo
                ORDER BY id_variante ASC;
                """,
                (id_producto,)
            )
            filas_var = cur.fetchall()

        # Sin variantes activas el producto no se puede vender: no es visible.
        if not filas_var:
            return None

        variantes = [
            VarianteProducto(
                id_variante=v["id_variante"],
                id_producto=v["id_producto"],
                sku=v["sku"],
                stock=v["stock"],
                talla=v["talla"],
                color=v["color"],
                compatibilidad=v["compatibilidad"],
                activo=v["activo"]
            )
            for v in filas_var
        ]

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
            activo=fila_prod["activo"],
            stock_total=sum(v.stock for v in variantes),
            variantes=variantes
        )
        return producto.to_dict(incluir_variantes=True)
