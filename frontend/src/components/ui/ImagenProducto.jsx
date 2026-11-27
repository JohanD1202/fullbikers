import { useState } from "react";

import s from "./ImagenProducto.module.css";

// Tono del marcador según la categoría, para distinguir productos sin foto.
const TONOS = ["#0F4C42", "#2B3A38", "#13604F", "#5E7A72", "#3D5A52"];

function tono(texto = "") {
  let h = 0;
  for (const c of texto) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return TONOS[h % TONOS.length];
}

/**
 * Imagen principal del producto (producto.imagen: URL o null). Sin imagen,
 * o si la URL falla, muestra un marcador con la referencia y la marca.
 */
export default function ImagenProducto({ src, nombre, referencia, marca, categoria, className = "", tamano = "md" }) {
  const [fallo, setFallo] = useState(false);
  if (src && !fallo) {
    return <img className={`${s.imagen} ${className}`} src={src} alt={nombre} loading="lazy" onError={() => setFallo(true)} />;
  }
  return (
    <div className={`${s.marcador} ${s[tamano]} ${className}`} style={{ "--tono": tono(categoria || nombre) }} role="img" aria-label={`${nombre} (sin fotografía)`}>
      <svg className={s.curva} viewBox="0 0 200 120" preserveAspectRatio="none" aria-hidden>
        <path d="M -10 120 C 60 110, 80 50, 130 40 S 190 20, 220 -10" stroke="rgba(255,255,255,0.08)" strokeWidth="46" fill="none" />
        <path d="M -10 120 C 60 110, 80 50, 130 40 S 190 20, 220 -10" stroke="var(--linea)" strokeWidth="2.5" strokeDasharray="8 9" fill="none" opacity="0.7" />
      </svg>
      {marca && <span className={s.marca}>{marca}</span>}
      {referencia && <span className={s.referencia}>{referencia}</span>}
    </div>
  );
}
