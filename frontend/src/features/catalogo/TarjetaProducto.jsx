import { forwardRef } from "react";
import { Link } from "react-router";
import { motion } from "motion/react";

import ImagenProducto from "../../components/ui/ImagenProducto";
import { formatoCOP } from "../../utils/format";
import s from "./Catalogo.module.css";

/** Tarjeta de ProductoResumen (API.md §5). */
const TarjetaProducto = forwardRef(function TarjetaProducto({ producto, indice = 0 }, ref) {
  return (
    <motion.li
      ref={ref}
      layout
      className={s.tarjeta}
      initial={{ opacity: 0, y: 18, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94, transition: { duration: 0.18 } }}
      transition={{ type: "spring", stiffness: 300, damping: 30, delay: Math.min(indice, 8) * 0.035 }}
    >
      <Link to={`/productos/${producto.id_producto}`} className={s.enlaceTarjeta}>
        <div className={s.fotoTarjeta}>
          <ImagenProducto
            src={producto.imagen}
            nombre={producto.nombre}
            referencia={producto.referencia}
            marca={producto.marca}
            categoria={producto.categoria}
          />
          {!producto.disponible ? (
            <span className={`${s.etiquetaStock} ${s.agotado}`}>Agotado</span>
          ) : producto.stock_total <= 5 ? (
            <span className={s.etiquetaStock}>Últimas {producto.stock_total}</span>
          ) : null}
        </div>
        <div className={s.cuerpoTarjeta}>
          <p className={s.categoriaTarjeta}>{producto.categoria}</p>
          <h3 className={s.nombreTarjeta}>{producto.nombre}</h3>
          <p className={`${s.precio} numero`}>{formatoCOP(producto.precio)}</p>
        </div>
      </Link>
    </motion.li>
  );
});

export default TarjetaProducto;
