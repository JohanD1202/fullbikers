# Consultas SQL de carrito y detalle_carrito (RF-12 a RF-15).
#
# Reglas DAO: conexión como primer argumento, SQL parametrizado, sin commit ni
# rollback: el servicio que llama (carrito o, más adelante, pedidos) abre la
# transacción con database.transaccion() y pasa la misma conexión a todos los
# DAO. Ver backend/API.md §9 (pedidos) y §10.
#
# Estados de carrito (CHECK ck_carrito_estado): abierto | convertido | abandonado.
# Como máximo un carrito abierto y activo por usuario (ux_carrito_abierto_por_usuario)
# y una línea activa por variante en cada carrito (ux_detalle_carrito_linea_activa).
from models.carrito import ItemCarrito

_COLUMNAS_CARRITO = "id_carrito, id_usuario, estado, fecha_creacion, activo"

_SELECT_ITEMS = """
    SELECT dc.id_detalle_carrito, dc.id_carrito, dc.id_producto, dc.id_variante, dc.cantidad,
           p.nombre, p.referencia, p.precio, p.imagen, p.marca, c.nombre AS categoria,
           v.sku, v.talla, v.color, v.compatibilidad, v.stock,
           p.activo AS producto_activo, c.activo AS categoria_activa, v.activo AS variante_activa
    FROM detalle_carrito dc
    JOIN producto p          ON p.id_producto = dc.id_producto
    JOIN categoria c         ON c.id_categoria = p.id_categoria
    JOIN variante_producto v ON v.id_variante = dc.id_variante AND v.id_producto = dc.id_producto
"""


class CarritoDAO:
    @staticmethod
    def obtener_abierto(conn, id_usuario, bloquear=False):
        """Carrito abierto y activo del usuario (dict) o None.

        bloquear=True: bloquea la fila del carrito hasta el fin de la
        transacción (FOR NO KEY UPDATE) para serializar las modificaciones
        concurrentes del mismo carrito; el módulo de pedidos debe usarlo al
        convertir el carrito.
        """
        sql = f"SELECT {_COLUMNAS_CARRITO} FROM carrito WHERE id_usuario = %s AND estado = 'abierto' AND activo"
        if bloquear:
            sql += " FOR NO KEY UPDATE"
        with conn.cursor() as cur:
            cur.execute(sql + ";", (id_usuario,))
            return cur.fetchone()

    @staticmethod
    def obtener_o_crear_abierto(conn, id_usuario):
        """Devuelve el carrito abierto (bloqueado), creándolo si no existe.

        ON CONFLICT sobre el índice único parcial evita crear dos carritos
        abiertos si llegan dos peticiones simultáneas del mismo usuario.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO carrito (id_usuario) VALUES (%s)
                ON CONFLICT (id_usuario) WHERE activo AND estado = 'abierto' DO NOTHING;
                """,
                (id_usuario,),
            )
        return CarritoDAO.obtener_abierto(conn, id_usuario, bloquear=True)

    @staticmethod
    def marcar_convertido(conn, id_carrito, id_usuario):
        """Transición condicional abierto -> convertido (registro de pedido).

        Devuelve True si el carrito estaba abierto y activo; False si ya había
        sido convertido o abandonado (el servicio debe abortar).
        """
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE carrito SET estado = 'convertido' "
                "WHERE id_carrito = %s AND id_usuario = %s AND estado = 'abierto' AND activo "
                "RETURNING id_carrito;",
                (id_carrito, id_usuario),
            )
            return cur.fetchone() is not None

    @staticmethod
    def listar_items(conn, id_carrito):
        """Líneas ACTIVAS del carrito con precio, stock y estado vigentes.

        No filtra productos, categorías ni variantes inactivos: el servicio los
        marca como no disponibles para que el cliente los vea y los retire.
        """
        with conn.cursor() as cur:
            cur.execute(_SELECT_ITEMS + " WHERE dc.id_carrito = %s AND dc.activo ORDER BY dc.id_detalle_carrito;",
                        (id_carrito,))
            return [ItemCarrito.desde_fila(f) for f in cur.fetchall()]

    @staticmethod
    def obtener_item_de_usuario(conn, id_detalle_carrito, id_usuario):
        """Línea activa del usuario con el estado de su carrito, o None si no es suya.

        Devuelve (item, carrito) y bloquea la fila del carrito.
        """
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT ca.id_carrito, ca.estado, ca.activo
                FROM detalle_carrito dc
                JOIN carrito ca ON ca.id_carrito = dc.id_carrito
                WHERE dc.id_detalle_carrito = %s AND dc.activo AND ca.id_usuario = %s
                FOR NO KEY UPDATE OF ca;
                """,
                (id_detalle_carrito, id_usuario),
            )
            carrito = cur.fetchone()
            if carrito is None:
                return None, None
            cur.execute(_SELECT_ITEMS + " WHERE dc.id_detalle_carrito = %s;", (id_detalle_carrito,))
            return ItemCarrito.desde_fila(cur.fetchone()), carrito

    @staticmethod
    def obtener_cantidad_activa(conn, id_carrito, id_variante):
        """(id_detalle_carrito, cantidad) de la línea activa de esa variante, o None."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id_detalle_carrito, cantidad FROM detalle_carrito "
                "WHERE id_carrito = %s AND id_variante = %s AND activo;",
                (id_carrito, id_variante),
            )
            return cur.fetchone()

    @staticmethod
    def reactivar_item(conn, id_carrito, id_variante, cantidad):
        """Reactiva la última línea retirada de esa variante. Devuelve su id o None."""
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE detalle_carrito SET activo = TRUE, cantidad = %s
                WHERE id_detalle_carrito = (
                    SELECT max(id_detalle_carrito) FROM detalle_carrito
                    WHERE id_carrito = %s AND id_variante = %s AND NOT activo)
                RETURNING id_detalle_carrito;
                """,
                (cantidad, id_carrito, id_variante),
            )
            fila = cur.fetchone()
        return fila["id_detalle_carrito"] if fila else None

    @staticmethod
    def insertar_item(conn, id_carrito, id_producto, id_variante, cantidad):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO detalle_carrito (id_carrito, id_producto, id_variante, cantidad) "
                "VALUES (%s, %s, %s, %s) RETURNING id_detalle_carrito;",
                (id_carrito, id_producto, id_variante, cantidad),
            )
            return cur.fetchone()["id_detalle_carrito"]

    @staticmethod
    def actualizar_cantidad(conn, id_detalle_carrito, cantidad):
        with conn.cursor() as cur:
            cur.execute("UPDATE detalle_carrito SET cantidad = %s WHERE id_detalle_carrito = %s AND activo;",
                        (cantidad, id_detalle_carrito))

    @staticmethod
    def desactivar_item(conn, id_detalle_carrito):
        """Retira la línea (borrado lógico)."""
        with conn.cursor() as cur:
            cur.execute("UPDATE detalle_carrito SET activo = FALSE WHERE id_detalle_carrito = %s AND activo;",
                        (id_detalle_carrito,))
