"""Carrito de compras del usuario autenticado (RF-12 a RF-15).

Reglas:
  * Cada usuario usa SU carrito abierto; se crea al agregar el primer artículo.
  * Siempre se indica una variante (también la variante base) y debe
    pertenecer al producto indicado.
  * Producto, categoría y variante deben estar activos para agregar o
    aumentar cantidades; la cantidad resultante no puede superar el stock.
  * El precio NUNCA viene del frontend: se usa producto.precio vigente y los
    importes se calculan con Decimal en el servidor.
  * Retirar = detalle_carrito.activo = false. Volver a agregar una variante
    retirada reactiva su línea anterior.
  * Solo se modifican carritos en estado "abierto". No se crean pedidos, no se
    reserva ni descuenta stock y no se generan movimientos de inventario: la
    disponibilidad comprobada aquí no garantiza la del momento del pedido.
"""
from config import database
from dao.carrito_dao import CarritoDAO
from dao.producto_dao import ProductoDAO
from exceptions import ConflictoError, RecursoNoEncontradoError
from models.carrito import ABIERTO, Carrito
from services import validacion

CAMPOS_AGREGAR = frozenset({"id_producto", "id_variante", "cantidad"})
CAMPOS_CANTIDAD = frozenset({"cantidad"})


def _carrito_con_items(conn, fila_carrito):
    if fila_carrito is None:
        return Carrito()  # sin carrito abierto: carrito vacío
    return Carrito(
        id_carrito=fila_carrito["id_carrito"],
        estado=fila_carrito["estado"],
        fecha_creacion=fila_carrito.get("fecha_creacion"),
        items=CarritoDAO.listar_items(conn, fila_carrito["id_carrito"]),
    )


def _validar_cantidad(datos, errores):
    return validacion.entero_positivo(datos, "cantidad", "La cantidad", errores)


def _exigir_vendible(producto_activo, categoria_activa, variante_activa):
    if not (producto_activo and categoria_activa and variante_activa):
        raise ConflictoError("El producto o la presentación seleccionada ya no está disponible.",
                             codigo="producto_no_disponible")


def _exigir_stock(cantidad, stock, cantidad_en_carrito=None):
    if cantidad > stock:
        detalles = {"stock_disponible": stock}
        if cantidad_en_carrito is not None:
            detalles["cantidad_en_carrito"] = cantidad_en_carrito
        raise ConflictoError("No hay unidades suficientes para la cantidad solicitada.",
                             codigo="stock_insuficiente", detalles=detalles)


def obtener_carrito(id_usuario):
    """RF-13 / RF-15: carrito abierto con importes; vacío si no existe."""
    with database.obtener_conexion() as conn:
        return _carrito_con_items(conn, CarritoDAO.obtener_abierto(conn, id_usuario))


def agregar_item(id_usuario, datos):
    """RF-12: agrega una variante o incrementa su cantidad. Devuelve el carrito."""
    validacion.exigir_objeto(datos)
    validacion.rechazar_campos_no_permitidos(datos, CAMPOS_AGREGAR)
    errores = {}
    id_producto = validacion.entero_positivo(datos, "id_producto", "El producto", errores)
    id_variante = validacion.entero_positivo(datos, "id_variante", "La variante", errores)
    cantidad = _validar_cantidad(datos, errores)
    validacion.lanzar_si_hay_errores(errores)

    with database.transaccion() as conn:
        variante = ProductoDAO.obtener_variante_para_venta(conn, id_variante)
        if variante is None:
            raise RecursoNoEncontradoError("La presentación seleccionada no existe.", codigo="variante_no_encontrada")
        if variante["id_producto"] != id_producto:
            validacion.lanzar_si_hay_errores({"id_variante": "La variante no corresponde al producto indicado."})
        _exigir_vendible(variante["producto_activo"], variante["categoria_activa"], variante["variante_activa"])

        carrito = CarritoDAO.obtener_o_crear_abierto(conn, id_usuario)
        linea = CarritoDAO.obtener_cantidad_activa(conn, carrito["id_carrito"], id_variante)
        en_carrito = linea["cantidad"] if linea else 0
        _exigir_stock(en_carrito + cantidad, variante["stock"], cantidad_en_carrito=en_carrito)

        if linea:
            CarritoDAO.actualizar_cantidad(conn, linea["id_detalle_carrito"], en_carrito + cantidad)
        elif CarritoDAO.reactivar_item(conn, carrito["id_carrito"], id_variante, cantidad) is None:
            CarritoDAO.insertar_item(conn, carrito["id_carrito"], id_producto, id_variante, cantidad)
        return _carrito_con_items(conn, carrito)


def _item_modificable(conn, id_usuario, id_detalle_carrito):
    item, carrito = CarritoDAO.obtener_item_de_usuario(conn, id_detalle_carrito, id_usuario)
    if item is None:
        # Inexistente, retirado o de otro usuario: no se revela cuál.
        raise RecursoNoEncontradoError("El artículo no existe en su carrito.", codigo="item_no_encontrado")
    if carrito["estado"] != ABIERTO or not carrito["activo"]:
        raise ConflictoError("El carrito ya no se puede modificar.", codigo="carrito_no_modificable")
    return item, carrito


def actualizar_cantidad(id_usuario, id_detalle_carrito, datos):
    """RF-13 (modificar cantidades): fija la nueva cantidad de una línea."""
    validacion.exigir_objeto(datos)
    validacion.rechazar_campos_no_permitidos(datos, CAMPOS_CANTIDAD)
    errores = {}
    cantidad = _validar_cantidad(datos, errores)
    validacion.lanzar_si_hay_errores(errores)

    with database.transaccion() as conn:
        item, carrito = _item_modificable(conn, id_usuario, id_detalle_carrito)
        _exigir_vendible(item.producto_activo, item.categoria_activa, item.variante_activa)
        _exigir_stock(cantidad, item.stock)
        CarritoDAO.actualizar_cantidad(conn, id_detalle_carrito, cantidad)
        return _carrito_con_items(conn, carrito)


def retirar_item(id_usuario, id_detalle_carrito):
    """RF-14 (retirar): borrado lógico de la línea; el carrito puede quedar vacío.

    Se permite retirar aunque el producto esté inactivo o sin stock.
    """
    with database.transaccion() as conn:
        _, carrito = _item_modificable(conn, id_usuario, id_detalle_carrito)
        CarritoDAO.desactivar_item(conn, id_detalle_carrito)
        return _carrito_con_items(conn, carrito)

