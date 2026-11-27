import { motion } from "motion/react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import s from "./Catalogo.module.css";

function paginasVisibles(actual, total) {
  const paginas = new Set([1, total, actual - 1, actual, actual + 1]);
  const lista = [...paginas].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
  const conHuecos = [];
  lista.forEach((p, i) => {
    if (i && p - lista[i - 1] > 1) conHuecos.push(`hueco-${p}`);
    conHuecos.push(p);
  });
  return conHuecos;
}

export default function Paginacion({ pagina, totalPaginas, alCambiar }) {
  if (totalPaginas <= 1) return null;
  return (
    <nav className={s.paginacion} aria-label="Paginación">
      <button type="button" className={s.paginaFlecha} onClick={() => alCambiar(pagina - 1)} disabled={pagina <= 1} aria-label="Página anterior">
        <ChevronLeft size={18} />
      </button>
      {paginasVisibles(pagina, totalPaginas).map((p) =>
        typeof p === "string" ? (
          <span key={p} className={s.hueco} aria-hidden>
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            className={`${s.paginaNumero} numero ${p === pagina ? s.paginaActual : ""}`}
            onClick={() => alCambiar(p)}
            aria-current={p === pagina ? "page" : undefined}
            aria-label={`Página ${p}`}
          >
            {p === pagina && <motion.span layoutId="pagina-actual" className={s.fondoPagina} transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
            <span>{p}</span>
          </button>
        )
      )}
      <button type="button" className={s.paginaFlecha} onClick={() => alCambiar(pagina + 1)} disabled={pagina >= totalPaginas} aria-label="Página siguiente">
        <ChevronRight size={18} />
      </button>
    </nav>
  );
}
