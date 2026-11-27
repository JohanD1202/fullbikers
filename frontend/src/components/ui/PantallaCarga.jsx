import LineaVial from "./LineaVial";

export default function PantallaCarga({ mensaje = "Cargando…" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{ display: "grid", placeItems: "center", alignContent: "center", gap: "1rem", minHeight: "60vh", color: "var(--musgo)" }}
    >
      <LineaVial bucle grosor={10} demora={0} className="carga-linea" />
      <p>{mensaje}</p>
      <style>{".carga-linea{width:160px}"}</style>
    </div>
  );
}
