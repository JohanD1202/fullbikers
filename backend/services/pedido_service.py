"""Registro y consulta de pedidos del usuario autenticado (RF-16 a RF-19).

Registrar un pedido es UNA transacción (database.transaccion()) que comparte
la misma conexión entre CarritoDAO, DireccionDAO, InventarioDAO y PedidoDAO.
Cualquier error revierte todo: no quedan pedidos sin líneas, descuentos sin
pedido, movimientos sueltos ni carritos convertidos sin pedido.

Orden (database/README.md §8.3, adaptado a las FK del esquema):
  1. Bloquear el carrito abierto del usuario (FOR NO KEY UPDATE). Una segunda
     petición simultánea espera aquí y, al continuar, ya no encuentra carrito
     abierto -> 409 carrito_vacio.
  2. Validar la dirección (activa y del usuario).
  3. Bloquear las variantes del carrito en orden ascendente de id_variante
     (evita interbloqueos entre pedidos concurrentes).
  4. Releer las líneas (precio vigente, stock y estados ya bloqueados) y
     validar disponibilidad de TODAS (RF-16). Si alguna falla: 409 con detalle.
  5. Calcular importes con Decimal y crear el pedido 'pendiente' con la copia
     de la dirección (RF-17, RF-18: id_pedido lo genera PostgreSQL).
  6. Insertar las líneas con el precio copiado (RF-19).
  7. Por línea: UPDATE condicional del stock + movimiento 'salida' (abortar si
     no hay stock: última barrera contra sobreventas).
  8. Transición condicional del carrito abierto -> convertido.
"""
import logging

from config import database
from dao.carrito_dao import CarritoDAO
from dao.direccion_dao import DireccionDAO
from dao.inventario_dao import InventarioDAO
from dao.pedido_dao import PedidoDAO
from exceptions import ConflictoError, RecursoNoEncontradoError
from models.dinero import a_decimal
from services import validacion

logger = logging.getLogger(__name__)

CAMPOS_PEDIDO = frozenset({"id_direccion", "observaciones"})
LONGITUD_OBSERVACIONES = 1000  # CHECK ck_pedido_observaciones_longitud


def _carrito_vacio():
    return ConflictoError("No hay artículos en el carrito para confirmar el pedido.", codigo="carrito_vacio")


def _validar_solicitud(datos):
    validacion.exigir_objeto(datos)
    validacion.rechazar_campos_no_permitidos(datos, CAMPOS_PEDIDO)
    errores = {}
    id_direccion = validacion.entero_positivo(datos, "id_direccion", "La dirección", errores)
    observaciones = validacion.texto(datos, "observaciones", "Las observaciones", errores,
                                     LONGITUD_OBSERVACIONES, obligatorio=False)
    validacion.lanzar_si_hay_errores(errores)
    return id_direccion, observaciones


def _exigir_disponibilidad(items):
    """RF-16: todas las líneas deben poder comprarse; si no, se informan todas."""
    problemas = [
        {
            "id_detalle_carrito": item.id_detalle_carrito,
            "id_variante": item.id_variante,
            "nombre": item.nombre,
            "motivo": item.motivo_no_disponible,
            "cantidad": item.cantidad,
            "stock_disponible": item.stock if item.motivo_no_disponible in ("sin_stock", "stock_insuficiente") else 0,
        }
        for item in items if not item.disponible
    ]
    if problemas:
        raise ConflictoError(
            "Algunos artículos del carrito no están disponibles en la cantidad solicitada.",
            codigo="articulos_no_disponibles",
            detalles={"items": problemas},
        )


def registrar_pedido(id_usuario, datos):
    """Confirma el carrito abierto del usuario como pedido. Devuelve el Pedido."""
    id_direccion, observaciones = _validar_solicitud(datos)

    with database.transaccion() as conn:
        carrito = CarritoDAO.obtener_abierto(conn, id_usuario, bloquear=True)
        if carrito is None:
            raise _carrito_vacio()
        id_carrito = carrito["id_carrito"]

        direccion = DireccionDAO.obtener_activa(conn, id_direccion, id_usuario)
        if direccion is None:
            raise RecursoNoEncontradoError("La dirección seleccionada no existe.", codigo="direccion_no_encontrada")

        items = CarritoDAO.listar_items(conn, id_carrito)
        if not items:
            raise _carrito_vacio()
        InventarioDAO.bloquear_variantes(conn, [item.id_variante for item in items])
        # Relectura con las variantes bloqueadas: stock, estados y precio definitivos.
        items = sorted(CarritoDAO.listar_items(conn, id_carrito), key=lambda item: item.id_variante)
        if not items:
            raise _carrito_vacio()
        _exigir_disponibilidad(items)

        subtotal = a_decimal(sum(item.subtotal for item in items))
        total = subtotal  # sin envío, impuestos ni descuentos en el alcance actual
        id_pedido = PedidoDAO.crear(conn, id_usuario, direccion, subtotal, total, observaciones)

        for item in items:
            PedidoDAO.insertar_detalle(conn, id_pedido, item.id_producto, item.id_variante,
                                       item.cantidad, item.precio)
        for item in items:
            movimiento = InventarioDAO.registrar_salida_por_pedido(
                conn, item.id_variante, item.cantidad, id_pedido, id_usuario,
                motivo=f"Venta: pedido {id_pedido}",
            )
            if movimiento is None:
                raise ConflictoError("No hay unidades suficientes para la cantidad solicitada.",
                                     codigo="stock_insuficiente",
                                     detalles={"id_variante": item.id_variante})

        if not CarritoDAO.marcar_convertido(conn, id_carrito, id_usuario):
            raise _carrito_vacio()

        pedido = PedidoDAO.obtener_de_usuario(conn, id_pedido, id_usuario)

    logger.info("Pedido registrado (id_pedido=%s, id_usuario=%s, lineas=%s).", id_pedido, id_usuario, len(items))
    return pedido


def obtener_pedido(id_usuario, id_pedido):
    """Detalle de un pedido propio con importes históricos; 404 si es ajeno o no existe."""
    with database.obtener_conexion() as conn:
        pedido = PedidoDAO.obtener_de_usuario(conn, id_pedido, id_usuario)
    if pedido is None:
        raise RecursoNoEncontradoError("El pedido solicitado no existe.", codigo="pedido_no_encontrado")
    return pedido
