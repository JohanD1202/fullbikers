# Actualización de existencias (variante_producto.stock) y bitácora
# movimiento_inventario. Ver database/README.md §8.
#
# Reglas:
#   * El stock SOLO cambia aquí y SIEMPRE junto con su movimiento, en la
#     transacción del servicio que llama (sin commit ni rollback).
#   * stock_anterior/stock_nuevo salen del propio UPDATE ... RETURNING, nunca de
#     un SELECT previo.
#   * Varias variantes en una transacción: procesarlas en orden ascendente de
#     id_variante para evitar interbloqueos.
#
# Próximos módulos: RF-29/RF-30 (entradas, salidas y ajustes manuales) y la
# cancelación de pedidos deben añadir sus métodos aquí siguiendo el mismo patrón.


class InventarioDAO:
    @staticmethod
    def bloquear_variantes(conn, ids_variante):
        """Bloquea las variantes (FOR NO KEY UPDATE) en orden ascendente de id.

        Tras este bloqueo, ninguna otra transacción puede cambiar su stock ni su
        estado hasta el COMMIT/ROLLBACK, de modo que las lecturas posteriores en
        la misma transacción son definitivas.
        """
        if not ids_variante:
            return
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id_variante FROM variante_producto WHERE id_variante = ANY(%s) "
                "ORDER BY id_variante FOR NO KEY UPDATE;",
                (sorted(ids_variante),),
            )
            cur.fetchall()

    @staticmethod
    def registrar_salida_por_pedido(conn, id_variante, cantidad, id_pedido, id_usuario, motivo):
        """Descuenta `cantidad` y registra el movimiento 'salida' del pedido.

        El UPDATE solo se aplica si la variante está activa y hay stock
        suficiente; devuelve {"stock_anterior", "stock_nuevo", "id_movimiento"}
        o None si no se pudo descontar (el servicio debe abortar la transacción).
        uq_movimiento_inventario_pedido_variante_tipo impide una segunda salida
        para el mismo pedido y variante.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH upd AS (
                    UPDATE variante_producto
                       SET stock = stock - %(cantidad)s
                     WHERE id_variante = %(id_variante)s
                       AND activo
                       AND stock >= %(cantidad)s
                    RETURNING id_variante, stock + %(cantidad)s AS stock_anterior, stock AS stock_nuevo
                )
                INSERT INTO movimiento_inventario
                       (id_variante, id_usuario, id_pedido, tipo, cantidad, stock_anterior, stock_nuevo, motivo)
                SELECT id_variante, %(id_usuario)s, %(id_pedido)s, 'salida', %(cantidad)s,
                       stock_anterior, stock_nuevo, %(motivo)s
                FROM upd
                RETURNING id_movimiento, stock_anterior, stock_nuevo;
                """,
                {"cantidad": cantidad, "id_variante": id_variante, "id_usuario": id_usuario,
                 "id_pedido": id_pedido, "motivo": motivo},
            )
            return cur.fetchone()
