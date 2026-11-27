import { useId } from "react";
import { motion, useReducedMotion } from "motion/react";

/**
 * Elemento distintivo de FullBikers: una curva de carretera con la línea
 * amarilla discontinua. Se "pavimenta" una vez (o en bucle como indicador de
 * carga) mediante una máscara animada, para que los guiones se conserven.
 */
export default function LineaVial({ className = "", bucle = false, grosor = 14, demora = 0.15 }) {
  const reducir = useReducedMotion();
  const id = useId().replace(/:/g, "");
  // La curva sale de los bordes del lienzo para que no se vea cortada.
  const trazo = "M -30 98 C 50 92, 70 42, 130 34 S 220 8, 310 2";
  return (
    <svg className={className} viewBox="0 0 280 100" fill="none" aria-hidden="true" overflow="visible">
      <defs>
        <mask id={`via-${id}`} maskUnits="userSpaceOnUse" x="-60" y="-60" width="400" height="220">
          <motion.path
            d={trazo}
            stroke="white"
            strokeWidth={grosor * 3}
            strokeLinecap="round"
            initial={reducir ? false : { pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{
              duration: 1.2,
              ease: [0.22, 1, 0.36, 1],
              delay: demora,
              repeat: bucle && !reducir ? Infinity : 0,
              repeatDelay: 0.35,
            }}
          />
        </mask>
      </defs>
      <g mask={`url(#via-${id})`}>
        <path d={trazo} stroke="var(--asfalto)" strokeWidth={grosor * 2.6} strokeLinecap="butt" />
        <path d={trazo} stroke="var(--linea)" strokeWidth={grosor * 0.3} strokeDasharray="10 11" />
      </g>
    </svg>
  );
}
