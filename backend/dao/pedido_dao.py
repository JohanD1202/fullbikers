# Consultas SQL de pedido y detalle_pedido (RF-16 a RF-19).
#
# Reglas DAO: conexión como primer argumento, SQL parametrizado, sin commit ni
# rollback. El servicio de pedidos abre UNA transacción y pasa la misma
# conexión a este DAO, a CarritoDAO, DireccionDAO e InventarioDAO.
# id_pedido e id_detalle los genera PostgreSQL (GENERATED ALWAYS AS IDENTITY).
from models.pedido import DetallePedido, Pedido

_COLUMNAS_PEDIDO = """
    id_pedido, id_usuario, id_direccion, fecha, estado, subtotal, total, observaciones,
    departamento_entrega, municipio_entrega, direccion_entrega, complemento_entrega,
    codigo_postal_entrega, fecha_actualizacion
"""


class PedidoDAO:
    @staticmethod
    def crear(conn, id_usuario, direccion, subtotal, total, observaciones):
        """Inserta el pedido en estado 'pendiente' con la COPIA de la dirección.

        `direccion` es un models.direccion.Direccion activa del mismo usuario
        (la FK compuesta fk_pedido_direccion_usuario también lo exige).
        Devuelve el id_pedido generado.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pedido (id_usuario, id_direccion, subtotal, total, observaciones,
                                    departamento_entrega, municipio_entrega, direccion_entrega,
                                    complemento_entrega, codigo_postal_entrega)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_pedido;
                """,
                (id_usuario, direccion.id_direccion, subtotal, total, observaciones,
                 direccion.departamento, direccion.municipio, direccion.direccion,
                 direccion.complemento, direccion.codigo_postal),
            )
            return cur.fetchone()["id_pedido"]

    @staticmethod
    def insertar_detalle(conn, id_pedido, id_producto, id_variante, cantidad, precio_unitario):
        """Inserta una línea con el precio vigente copiado. subtotal lo calcula
        PostgreSQL (columna generada cantidad * precio_unitario) y se devuelve."""
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detalle_pedido (id_pedido, id_producto, id_variante, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_detalle, subtotal;
                """,
                (id_pedido, id_producto, id_variante, cantidad, precio_unitario),
            )
            return cur.fetchone()

    @staticmethod
    def obtener_de_usuario(conn, id_pedido, id_usuario):
        """Pedido activo del usuario con sus líneas, o None si no existe o es ajeno."""
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNAS_PEDIDO} FROM pedido WHERE id_pedido = %s AND id_usuario = %s AND activo;",
                (id_pedido, id_usuario),
            )
            fila = cur.fetchone()
        if fila is None:
            return None
        return Pedido.desde_fila(fila, detalles=PedidoDAO.listar_detalles(conn, id_pedido))

    @staticmethod
    def listar_detalles(conn, id_pedido):
        """Líneas del pedido con importes históricos y la descripción ACTUAL del
        producto/variante (aunque estén inactivos)."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id_detalle, d.id_producto, d.id_variante, d.cantidad, d.precio_unitario, d.subtotal,
                       p.nombre, p.referencia, p.imagen, v.sku, v.talla, v.color, v.compatibilidad
                FROM detalle_pedido d
                JOIN producto p          ON p.id_producto = d.id_producto
                JOIN variante_producto v ON v.id_variante = d.id_variante
                WHERE d.id_pedido = %s AND d.activo
                ORDER BY d.id_detalle;
                """,
                (id_pedido,),
            )
            return [DetallePedido.desde_fila(f) for f in cur.fetchall()]
