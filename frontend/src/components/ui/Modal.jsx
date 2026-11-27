import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";

import s from "./Modal.module.css";

/**
 * Ventana modal accesible: foco atrapado, Escape para cerrar, clic en el fondo.
 * `lado="derecha"` la convierte en panel lateral (cajón del carrito).
 */
export default function Modal({ abierto, alCerrar, titulo, children, pie, lado = "centro", ancho }) {
  const idTitulo = useId();
  const panel = useRef(null);
  const anterior = useRef(null);
  const cerrarRef = useRef(alCerrar);
  cerrarRef.current = alCerrar;

  useEffect(() => {
    if (!abierto) return;
    anterior.current = document.activeElement;
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";

    const alTeclear = (e) => {
      if (e.key === "Escape") cerrarRef.current();
      if (e.key !== "Tab" || !panel.current) return;
      const enfocables = panel.current.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!enfocables.length) return;
      const primero = enfocables[0];
      const ultimo = enfocables[enfocables.length - 1];
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    };
    document.addEventListener("keydown", alTeclear);
    const temporizador = window.setTimeout(() => panel.current?.focus(), 30);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", alTeclear);
      window.clearTimeout(temporizador);
      anterior.current?.focus?.();
    };
  }, [abierto]);

  const lateral = lado === "derecha";
  const animacion = lateral
    ? { initial: { x: "100%" }, animate: { x: 0 }, exit: { x: "100%" } }
    : { initial: { opacity: 0, y: 28, scale: 0.97 }, animate: { opacity: 1, y: 0, scale: 1 }, exit: { opacity: 0, y: 16, scale: 0.98 } };

  return createPortal(
    <AnimatePresence>
      {abierto && (
        <div className={`${s.capa} ${lateral ? s.capaLateral : ""}`}>
          <motion.div
            className={s.fondo}
            onClick={alCerrar}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.section
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-labelledby={idTitulo}
            tabIndex={-1}
            className={`${s.panel} ${lateral ? s.lateral : ""}`}
            style={ancho ? { maxWidth: ancho } : undefined}
            {...animacion}
            transition={{ type: "spring", stiffness: 380, damping: 36 }}
          >
            <header className={s.cabecera}>
              <h2 id={idTitulo} className={s.titulo}>
                {titulo}
              </h2>
              <button type="button" className={s.cerrar} onClick={alCerrar} aria-label="Cerrar">
                <X size={20} />
              </button>
            </header>
            <div className={s.cuerpo}>{children}</div>
            {pie && <footer className={s.pie}>{pie}</footer>}
          </motion.section>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
