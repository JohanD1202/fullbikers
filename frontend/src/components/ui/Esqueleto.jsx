import s from "./Esqueleto.module.css";

export default function Esqueleto({ alto = "1rem", ancho = "100%", radio, className = "" }) {
  return <span className={`${s.esqueleto} ${className}`} style={{ height: alto, width: ancho, borderRadius: radio }} aria-hidden />;
}
