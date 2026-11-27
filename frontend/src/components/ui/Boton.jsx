import { forwardRef } from "react";
import { Link } from "react-router";
import { Loader2 } from "lucide-react";

import s from "./Boton.module.css";

/**
 * Botón de la interfaz. variante: primario | acento | secundario | fantasma | peligro.
 * Con `to` se comporta como enlace de React Router. `cargando` lo deshabilita
 * y muestra un indicador (evita dobles envíos).
 */
const Boton = forwardRef(function Boton(
  { variante = "primario", tamano = "md", cargando = false, icono: Icono, to, className = "", children, disabled, ...props },
  ref
) {
  const clases = [s.boton, s[variante], s[tamano], cargando ? s.cargando : "", className].join(" ");
  const contenido = (
    <>
      {cargando ? <Loader2 className={s.giro} size={18} aria-hidden /> : Icono ? <Icono size={18} aria-hidden /> : null}
      {children && <span>{children}</span>}
    </>
  );
  if (to) {
    return (
      <Link ref={ref} to={to} className={clases} {...props}>
        {contenido}
      </Link>
    );
  }
  return (
    <button ref={ref} className={clases} disabled={disabled || cargando} aria-busy={cargando || undefined} {...props}>
      {contenido}
    </button>
  );
});

export default Boton;
