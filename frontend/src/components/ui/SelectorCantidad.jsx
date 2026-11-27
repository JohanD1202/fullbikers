import { AnimatePresence, motion } from "motion/react";
import { Minus, Plus } from "lucide-react";

import s from "./SelectorCantidad.module.css";

/** Selector − n + con animación del número. `max` limita al stock disponible. */
export default function SelectorCantidad({ valor, alCambiar, min = 1, max = Infinity, deshabilitado = false, etiqueta = "Cantidad", tamano = "md" }) {
  const cambiar = (n) => {
    const limitado = Math.min(Math.max(n, min), max);
    if (limitado !== valor) alCambiar(limitado);
  };
  return (
    <div className={`${s.selector} ${s[tamano]}`} role="group" aria-label={etiqueta}>
      <button type="button" onClick={() => cambiar(valor - 1)} disabled={deshabilitado || valor <= min} aria-label="Disminuir cantidad">
        <Minus size={16} />
      </button>
      <span className={`${s.valor} numero`} aria-live="polite">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.span
            key={valor}
            initial={{ y: -12, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 12, opacity: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
          >
            {valor}
          </motion.span>
        </AnimatePresence>
      </span>
      <button type="button" onClick={() => cambiar(valor + 1)} disabled={deshabilitado || valor >= max} aria-label="Aumentar cantidad">
        <Plus size={16} />
      </button>
    </div>
  );
}
