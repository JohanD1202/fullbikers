import { motion } from "motion/react";

import LineaVial from "../../components/ui/LineaVial";
import Logo from "../../components/layout/Logo";
import s from "./Auth.module.css";

/** Marco de login y registro: la vía se dibuja una vez junto al formulario. */
export default function AuthLayout({ titulo, subtitulo, children }) {
  return (
    <div className={s.pagina}>
      <aside className={s.escena} aria-hidden>
        <Logo claro />
        <LineaVial className={s.via} grosor={16} demora={0.2} />
        <motion.p
          className={s.lema}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          Cascos, guantes, chaquetas y todo lo que va contigo en la vía.
        </motion.p>
      </aside>
      <main className={s.panel}>
        <motion.div
          className={s.formulario}
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className={s.logoMovil}>
            <Logo />
          </div>
          <h1 className={s.titulo}>{titulo}</h1>
          {subtitulo && <p className={s.subtitulo}>{subtitulo}</p>}
          {children}
        </motion.div>
      </main>
    </div>
  );
}
