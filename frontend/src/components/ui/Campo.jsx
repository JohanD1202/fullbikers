import { useId, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Eye, EyeOff } from "lucide-react";

import s from "./Campo.module.css";

/**
 * Campo de formulario con etiqueta flotante, ayuda y error animado.
 * `multilinea` usa <textarea>. Tipo "password" añade botón para mostrarla.
 */
export default function Campo({ etiqueta, error, ayuda, multilinea = false, type = "text", className = "", contador, ...props }) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const esClave = type === "password";
  const Control = multilinea ? "textarea" : "input";
  const descripcion = [error ? `${id}-error` : null, ayuda ? `${id}-ayuda` : null].filter(Boolean).join(" ") || undefined;
  const longitud = typeof props.value === "string" ? props.value.length : 0;

  return (
    <div className={`${s.campo} ${error ? s.conError : ""} ${className}`}>
      <div className={s.marco}>
        <Control
          id={id}
          className={`${s.control} ${multilinea ? s.area : ""} ${esClave ? s.conOjo : ""}`}
          type={multilinea ? undefined : esClave && visible ? "text" : type}
          placeholder=" "
          aria-invalid={error ? true : undefined}
          aria-describedby={descripcion}
          {...props}
        />
        <label htmlFor={id} className={s.etiqueta}>
          {etiqueta}
          {props.required && <span aria-hidden> *</span>}
        </label>
        {esClave && (
          <button
            type="button"
            className={s.ojo}
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          >
            {visible ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      <div className={s.pie}>
        <AnimatePresence initial={false} mode="wait">
          {error ? (
            <motion.p
              key="error"
              id={`${id}-error`}
              className={s.error}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
            >
              {error}
            </motion.p>
          ) : ayuda ? (
            <p key="ayuda" id={`${id}-ayuda`} className={s.ayuda}>
              {ayuda}
            </p>
          ) : null}
        </AnimatePresence>
        {contador && (
          <span className={`${s.contador} numero`}>
            {longitud}/{contador}
          </span>
        )}
      </div>
    </div>
  );
}
