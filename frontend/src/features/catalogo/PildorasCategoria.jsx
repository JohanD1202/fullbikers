import { motion } from "motion/react";

import s from "./Catalogo.module.css";

/** Filtro por categoría: la píldora activa se desliza hasta la elegida. */
export default function PildorasCategoria({ categorias, activa, alElegir, idGrupo = "categorias" }) {
  const opciones = [{ id_categoria: null, nombre: "Todo" }, ...categorias];
  return (
    <div className={s.pildoras} role="radiogroup" aria-label="Filtrar por categoría">
      {opciones.map((c) => {
        const seleccionada = (activa ?? null) === c.id_categoria;
        return (
          <button
            key={c.id_categoria ?? "todo"}
            type="button"
            role="radio"
            aria-checked={seleccionada}
            className={`${s.pildora} ${seleccionada ? s.pildoraActiva : ""}`}
            onClick={() => alElegir(c.id_categoria)}
          >
            {seleccionada && <motion.span layoutId={`${idGrupo}-activa`} className={s.fondoPildora} transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
            <span className={s.textoPildora}>{c.nombre}</span>
          </button>
        );
      })}
    </div>
  );
}
