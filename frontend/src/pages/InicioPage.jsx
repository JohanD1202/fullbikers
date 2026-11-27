import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { motion } from "motion/react";
import { ServerCrash } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { usePrincipal } from "../features/catalogo/usePrincipal";
import Buscador from "../features/catalogo/Buscador";
import GrillaProductos from "../features/catalogo/GrillaProductos";
import LineaVial from "../components/ui/LineaVial";
import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";
import Esqueleto from "../components/ui/Esqueleto";
import { plural } from "../utils/format";
import s from "./InicioPage.module.css";

function saludo() {
  const hora = Number(new Intl.DateTimeFormat("es-CO", { hour: "numeric", hourCycle: "h23", timeZone: "America/Bogota" }).format(new Date()));
  if (hora < 12) return "Buenos días";
  if (hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

export default function InicioPage() {
  const { usuario } = useAuth();
  const navegar = useNavigate();
  const [busqueda, setBusqueda] = useState("");
  const { data, isPending, isError, error, refetch } = usePrincipal();

  const buscar = (texto) => navegar(texto ? `/productos?busqueda=${encodeURIComponent(texto)}` : "/productos");

  return (
    <>
      <section className={s.hero}>
        <div className={`contenedor ${s.heroContenido}`}>
          <motion.p className={s.saludo} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
            {saludo()}, {usuario.nombre}
          </motion.p>
          <motion.h1
            className={s.titular}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            ¿Qué necesitas para la próxima rodada?
          </motion.h1>
          <motion.div
            className={s.busqueda}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <Buscador valor={busqueda} alCambiar={setBusqueda} alEnviar={buscar} grande />
          </motion.div>

          {data?.categorias?.length > 0 && (
            <motion.ul
              className={s.categorias}
              initial="oculto"
              animate="visible"
              variants={{ visible: { transition: { staggerChildren: 0.06, delayChildren: 0.55 } } }}
            >
              {data.categorias.map((c) => (
                <motion.li key={c.id_categoria} variants={{ oculto: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}>
                  <Link to={`/productos?categoria=${c.id_categoria}`} className={s.categoria} title={c.descripcion ?? undefined}>
                    {c.nombre}
                  </Link>
                </motion.li>
              ))}
            </motion.ul>
          )}
        </div>
        <LineaVial className={s.via} grosor={18} demora={0.25} />
      </section>

      <section className="contenedor" aria-labelledby="titulo-novedades">
        <div className={s.encabezadoSeccion}>
          <div>
            <h2 id="titulo-novedades" className={s.tituloSeccion}>
              Lo más reciente
            </h2>
            {data && <p className={s.descripcion}>{plural(data.total_productos, "producto disponible", "productos disponibles")} en el catálogo.</p>}
            {isPending && <Esqueleto alto="1rem" ancho="200px" />}
          </div>
          <Boton variante="secundario" to="/productos">
            Ver todo el catálogo
          </Boton>
        </div>

        {isError ? (
          <EstadoVacio icono={ServerCrash} tono="error" titulo="No pudimos cargar el catálogo" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
            {error.message}
          </EstadoVacio>
        ) : data && data.productos.length === 0 ? (
          <EstadoVacio titulo="Aún no hay productos publicados">Cuando el equipo de FullBikers publique productos, aparecerán aquí.</EstadoVacio>
        ) : (
          <GrillaProductos productos={data?.productos ?? []} cargando={isPending} />
        )}
      </section>
    </>
  );
}
