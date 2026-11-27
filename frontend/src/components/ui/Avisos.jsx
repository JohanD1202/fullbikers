// Notificaciones breves (toasts) que confirman lo que acaba de pasar.
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

import s from "./Avisos.module.css";

const AvisosContext = createContext(null);
const ICONOS = { exito: CheckCircle2, error: AlertTriangle, info: Info };

export function AvisosProvider({ children }) {
  const [avisos, setAvisos] = useState([]);
  const siguiente = useRef(1);

  const cerrar = useCallback((id) => setAvisos((lista) => lista.filter((a) => a.id !== id)), []);

  const avisar = useCallback(
    (mensaje, { tipo = "exito", duracion = 4200 } = {}) => {
      const id = siguiente.current++;
      setAvisos((lista) => [...lista.slice(-2), { id, mensaje, tipo }]);
      window.setTimeout(() => cerrar(id), duracion);
    },
    [cerrar]
  );

  const valor = useMemo(() => ({ avisar }), [avisar]);

  return (
    <AvisosContext.Provider value={valor}>
      {children}
      <div className={s.zona} aria-live="polite" aria-atomic="false">
        <AnimatePresence initial={false}>
          {avisos.map((aviso) => {
            const Icono = ICONOS[aviso.tipo] ?? Info;
            return (
              <motion.div
                key={aviso.id}
                layout
                className={`${s.aviso} ${s[aviso.tipo]}`}
                role={aviso.tipo === "error" ? "alert" : "status"}
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, transition: { duration: 0.18 } }}
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
              >
                <Icono size={20} aria-hidden className={s.icono} />
                <p>{aviso.mensaje}</p>
                <button type="button" className={s.cerrar} onClick={() => cerrar(aviso.id)} aria-label="Cerrar aviso">
                  <X size={16} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </AvisosContext.Provider>
  );
}

export function useAvisos() {
  const contexto = useContext(AvisosContext);
  if (!contexto) throw new Error("useAvisos debe usarse dentro de <AvisosProvider>.");
  return contexto;
}
