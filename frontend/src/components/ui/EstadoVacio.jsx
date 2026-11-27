import s from "./EstadoVacio.module.css";

/** Pantalla vacía o de error: explica qué pasa y qué hacer. */
export default function EstadoVacio({ icono: Icono, titulo, children, accion, tono = "neutro" }) {
  return (
    <div className={`${s.vacio} ${s[tono] ?? ""}`} role={tono === "error" ? "alert" : undefined}>
      {Icono && (
        <span className={s.icono}>
          <Icono size={26} aria-hidden />
        </span>
      )}
      <h2 className={s.titulo}>{titulo}</h2>
      {children && <div className={s.texto}>{children}</div>}
      {accion && <div className={s.accion}>{accion}</div>}
    </div>
  );
}
