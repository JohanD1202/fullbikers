import { AnimatePresence, motion } from "motion/react";
import { Link } from "react-router";
import { AlertTriangle, Trash2 } from "lucide-react";

import ImagenProducto from "../../components/ui/ImagenProducto";
import SelectorCantidad from "../../components/ui/SelectorCantidad";
import Boton from "../../components/ui/Boton";
import { useAvisos } from "../../components/ui/Avisos";
import { describirVariante, formatoCOP } from "../../utils/format";
import { MOTIVOS, useActualizarCantidad, useRetirarDelCarrito } from "./useCarrito";
import s from "./ListaCarrito.module.css";

/** Líneas del carrito con cantidad editable, retiro y avisos de disponibilidad. */
export default function ListaCarrito({ carrito, compacto = false, alNavegar }) {
  return (
    <ul className={`${s.lista} ${compacto ? s.compacto : ""}`}>
      <AnimatePresence initial={false}>
        {carrito.items.map((item) => (
          <LineaCarrito key={item.id_detalle_carrito} item={item} compacto={compacto} alNavegar={alNavegar} />
        ))}
      </AnimatePresence>
    </ul>
  );
}

function LineaCarrito({ item, compacto, alNavegar }) {
  const { avisar } = useAvisos();
  const actualizar = useActualizarCantidad();
  const retirar = useRetirarDelCarrito();
  const ocupado = actualizar.isPending || retirar.isPending;

  const cambiarCantidad = (cantidad) =>
    actualizar.mutate(
      { id: item.id_detalle_carrito, cantidad },
      { onError: (e) => avisar(e.message, { tipo: "error" }) }
    );

  const retirarLinea = () =>
    retirar.mutate(item.id_detalle_carrito, {
      onSuccess: () => avisar(`Retiraste ${item.nombre} del carrito.`),
      onError: (e) => avisar(e.message, { tipo: "error" }),
    });

  const maximo = item.disponible ? Math.max(item.stock_disponible, item.cantidad) : item.cantidad;
  const puedeAjustar = item.motivo_no_disponible === "stock_insuficiente" && item.stock_disponible > 0;

  return (
    <motion.li
      layout
      className={`${s.linea} ${item.disponible ? "" : s.noDisponible}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: ocupado ? 0.6 : 1, y: 0 }}
      exit={{ opacity: 0, x: -40, height: 0, marginBottom: 0, paddingBlock: 0, transition: { duration: 0.25 } }}
      transition={{ type: "spring", stiffness: 380, damping: 34 }}
    >
      <Link to={`/productos/${item.id_producto}`} className={s.foto} onClick={alNavegar} tabIndex={-1} aria-hidden>
        <ImagenProducto src={item.imagen} nombre={item.nombre} referencia={item.referencia} marca={item.marca} categoria={item.categoria} tamano="sm" />
      </Link>

      <div className={s.info}>
        <Link to={`/productos/${item.id_producto}`} className={s.nombre} onClick={alNavegar}>
          {item.nombre}
        </Link>
        <p className={s.variante}>
          {describirVariante(item)}
          {!compacto && <span className={s.sku}> SKU {item.sku}</span>}
        </p>
        <p className={`${s.unitario} numero`}>{formatoCOP(item.precio_unitario)} c/u</p>

        {!item.disponible && (
          <div className={s.aviso} role="status">
            <AlertTriangle size={16} aria-hidden />
            <span>
              {MOTIVOS[item.motivo_no_disponible] ?? "Este artículo no está disponible."}
              {item.motivo_no_disponible === "stock_insuficiente" && ` Disponibles: ${item.stock_disponible}.`}
            </span>
            {puedeAjustar && (
              <Boton tamano="sm" variante="secundario" onClick={() => cambiarCantidad(item.stock_disponible)} disabled={ocupado}>
                Ajustar a {item.stock_disponible}
              </Boton>
            )}
          </div>
        )}
      </div>

      <div className={s.controles}>
        <strong className={`${s.subtotal} numero`}>{formatoCOP(item.subtotal)}</strong>
        <div className={s.fila}>
          {item.disponible || puedeAjustar ? (
            <SelectorCantidad
              tamano="sm"
              valor={item.cantidad}
              max={puedeAjustar ? item.stock_disponible : maximo}
              alCambiar={cambiarCantidad}
              deshabilitado={ocupado}
              etiqueta={`Cantidad de ${item.nombre}`}
            />
          ) : (
            <span className={s.cantidadFija}>×{item.cantidad}</span>
          )}
          <button type="button" className={s.retirar} onClick={retirarLinea} disabled={ocupado} aria-label={`Retirar ${item.nombre}`}>
            <Trash2 size={17} />
          </button>
        </div>
      </div>
    </motion.li>
  );
}
