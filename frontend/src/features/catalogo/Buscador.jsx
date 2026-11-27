import { Search, X } from "lucide-react";

import s from "./Buscador.module.css";

/** Caja de búsqueda por nombre o referencia (máx. 100 caracteres, API.md §5). */
export default function Buscador({ valor, alCambiar, alEnviar, grande = false, autoFocus = false }) {
  return (
    <form
      role="search"
      className={`${s.buscador} ${grande ? s.grande : ""}`}
      onSubmit={(e) => {
        e.preventDefault();
        alEnviar?.(valor.trim());
      }}
    >
      <Search size={grande ? 22 : 19} className={s.lupa} aria-hidden />
      <label htmlFor="busqueda" className="visually-hidden">
        Buscar productos por nombre o referencia
      </label>
      <input
        id="busqueda"
        type="search"
        className={s.entrada}
        placeholder="Busca un casco, unos guantes o una referencia"
        value={valor}
        maxLength={100}
        autoFocus={autoFocus}
        autoComplete="off"
        onChange={(e) => alCambiar(e.target.value)}
      />
      {valor && (
        <button type="button" className={s.limpiar} onClick={() => alCambiar("")} aria-label="Borrar búsqueda">
          <X size={16} />
        </button>
      )}
      {alEnviar && (
        <button type="submit" className={s.ir}>
          Buscar
        </button>
      )}
    </form>
  );
}
