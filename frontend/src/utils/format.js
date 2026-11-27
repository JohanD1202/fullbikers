// Formatos de presentación (backend/API.md §1).

const pesos = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

/** "450000.00" -> "$ 450.000". La API envía el dinero como cadena decimal. */
export function formatoCOP(valor) {
  if (valor === null || valor === undefined || valor === "") return "";
  return pesos.format(Number(valor));
}

const fechaLarga = new Intl.DateTimeFormat("es-CO", {
  timeZone: "America/Bogota",
  dateStyle: "long",
  timeStyle: "short",
});

/** Fecha ISO 8601 (UTC) mostrada en hora de Colombia. */
export function formatoFecha(iso) {
  if (!iso) return "";
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? "" : fechaLarga.format(fecha);
}

/** Descripción legible de una variante: "M / Negro mate". */
export function describirVariante(v) {
  const partes = [v.talla, v.color, v.compatibilidad].filter(Boolean);
  return partes.length ? partes.join(" / ") : "Única";
}

export function plural(n, singular, pluralTexto = `${singular}s`) {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}
