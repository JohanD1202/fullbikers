// Estado de formularios: valores, errores por campo (del navegador y de la
// API) y campos tocados. Los errores 400 "validacion" de la API llegan en
// detalles.campos y se muestran junto a cada campo.
import { useCallback, useState } from "react";

import { soloErrores } from "../utils/validacion";

export default function useFormulario(valoresIniciales, validar) {
  const [valores, setValores] = useState(valoresIniciales);
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState(null);

  const cambiar = useCallback((campo, valor) => {
    setValores((v) => ({ ...v, [campo]: valor }));
    setErrores((e) => (e[campo] ? { ...e, [campo]: null } : e));
  }, []);

  /** Props listas para <Campo>: value, onChange, onBlur y error. */
  const campo = (nombre) => ({
    name: nombre,
    value: valores[nombre] ?? "",
    onChange: (e) => cambiar(nombre, e.target.value),
    onBlur: () => {
      if (!validar) return;
      const mensaje = validar(valores)[nombre];
      setErrores((e) => ({ ...e, [nombre]: mensaje || null }));
    },
    error: errores[nombre] || null,
  });

  /** Valida todo; devuelve true si no hay errores. */
  const validarTodo = () => {
    if (!validar) return true;
    const encontrados = soloErrores(validar(valores));
    setErrores(encontrados);
    return Object.keys(encontrados).length === 0;
  };

  /** Reparte un ApiError: errores por campo o mensaje general. */
  const aplicarErrorApi = (error, mapaCampos = {}) => {
    // Errores de un campo concreto que llegan sin detalles.campos (API.md §1).
    if (error?.codigo === "correo_ya_registrado" && "correo" in valores) {
      setErrores({ correo: error.message });
      setErrorGeneral(null);
      return;
    }
    const campos = error?.campos ?? {};
    const porCampo = {};
    const sueltos = [];
    for (const [clave, mensaje] of Object.entries(campos)) {
      const destino = mapaCampos[clave] ?? clave;
      if (destino in valores) porCampo[destino] = mensaje;
      else sueltos.push(mensaje);
    }
    setErrores(porCampo);
    const hayCampos = Object.keys(porCampo).length > 0;
    setErrorGeneral(hayCampos && !sueltos.length ? null : sueltos[0] || error?.message || "No fue posible completar la acción.");
  };

  return { valores, setValores, errores, setErrores, errorGeneral, setErrorGeneral, cambiar, campo, validarTodo, aplicarErrorApi };
}
