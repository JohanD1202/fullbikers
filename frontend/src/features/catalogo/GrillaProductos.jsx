import { AnimatePresence } from "motion/react";

import Esqueleto from "../../components/ui/Esqueleto";
import TarjetaProducto from "./TarjetaProducto";
import s from "./Catalogo.module.css";

/** Cuadrícula que reacomoda las tarjetas con animación al filtrar o buscar. */
export default function GrillaProductos({ productos, cargando, cantidadEsqueletos = 8, atenuada = false }) {
  if (cargando) {
    return (
      <ul className={s.grilla} aria-busy="true" aria-label="Cargando productos">
        {Array.from({ length: cantidadEsqueletos }, (_, i) => (
          <li key={i} className={s.tarjeta}>
            <Esqueleto alto="auto" className={s.esqueletoFoto} radio="var(--r-superficie) var(--r-superficie) var(--r-superficie) 48px" />
            <div className={s.cuerpoTarjeta}>
              <Esqueleto alto="0.8rem" ancho="40%" />
              <Esqueleto alto="1.1rem" ancho="85%" />
              <Esqueleto alto="1.3rem" ancho="50%" />
            </div>
          </li>
        ))}
      </ul>
    );
  }
  return (
    <ul className={`${s.grilla} ${atenuada ? s.atenuada : ""}`}>
      <AnimatePresence mode="popLayout" initial={false}>
        {productos.map((p, i) => (
          <TarjetaProducto key={p.id_producto} producto={p} indice={i} />
        ))}
      </AnimatePresence>
    </ul>
  );
}
