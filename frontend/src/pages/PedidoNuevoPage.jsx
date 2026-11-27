// Confirmar el carrito como pedido (RF-16 a RF-19, API.md §9).
// Paso 1: dirección de entrega. Paso 2: revisión y confirmación.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Check, MapPin, Plus } from "lucide-react";

import { pedidosApi } from "../api/endpoints";
import { CLAVE_CARRITO, useCarrito } from "../features/carrito/useCarrito";
import { CLAVE_DIRECCIONES, useDirecciones } from "../features/direcciones/useDirecciones";
import FormularioDireccion from "../features/direcciones/FormularioDireccion";
import { textoDireccion } from "../features/direcciones/ListaDirecciones";
import ImagenProducto from "../components/ui/ImagenProducto";
import Campo from "../components/ui/Campo";
import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";
import PantallaCarga from "../components/ui/PantallaCarga";
import { useAvisos } from "../components/ui/Avisos";
import { describirVariante, formatoCOP, plural } from "../utils/format";
import s from "./PedidoNuevoPage.module.css";

const PASOS = ["Entrega", "Revisión"];

export default function PedidoNuevoPage() {
  const navegar = useNavigate();
  const clienteQuery = useQueryClient();
  const { avisar } = useAvisos();
  const carritoQ = useCarrito();
  const direccionesQ = useDirecciones();
  const [paso, setPaso] = useState(0);
  const [idDireccion, setIdDireccion] = useState(null);
  const [observaciones, setObservaciones] = useState("");
  const [nueva, setNueva] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const enviado = useRef(false);

  const direcciones = direccionesQ.data ?? [];
  const carrito = carritoQ.data;

  // Preseleccionar la principal (o la primera) cuando llegan las direcciones.
  useEffect(() => {
    if (!direcciones.length) return;
    if (!direcciones.some((d) => d.id_direccion === idDireccion)) {
      setIdDireccion((direcciones.find((d) => d.principal) ?? direcciones[0]).id_direccion);
    }
  }, [direcciones, idDireccion]);

  if (carritoQ.isPending || direccionesQ.isPending) return <PantallaCarga mensaje="Preparando tu pedido…" />;
  if (carritoQ.isError || direccionesQ.isError) {
    return (
      <div className="contenedor">
        <EstadoVacio tono="error" titulo="No pudimos preparar tu pedido" accion={<Boton onClick={() => { carritoQ.refetch(); direccionesQ.refetch(); }}>Reintentar</Boton>}>
          {(carritoQ.error ?? direccionesQ.error).message}
        </EstadoVacio>
      </div>
    );
  }
  if (carrito.vacio && !enviado.current) {
    return (
      <div className="contenedor">
        <EstadoVacio titulo="No hay artículos para el pedido" accion={<Boton to="/productos">Explorar el catálogo</Boton>}>
          Agrega productos a tu carrito para registrar un pedido.
        </EstadoVacio>
      </div>
    );
  }
  if (!carrito.todos_disponibles && !enviado.current) {
    return (
      <div className="contenedor">
        <EstadoVacio titulo="Revisa tu carrito antes de continuar" accion={<Boton to="/carrito">Ir al carrito</Boton>}>
          Algunos artículos ya no están disponibles o superan las existencias.
        </EstadoVacio>
      </div>
    );
  }

  const direccion = direcciones.find((d) => d.id_direccion === idDireccion);

  const confirmar = async () => {
    if (!direccion || enviando) return;
    setEnviando(true);
    setError(null);
    try {
      const { pedido } = await pedidosApi.registrar({ id_direccion: direccion.id_direccion, observaciones: observaciones.trim() });
      enviado.current = true;
      // El carrito quedó convertido: el siguiente GET devuelve uno vacío.
      clienteQuery.invalidateQueries({ queryKey: CLAVE_CARRITO });
      ["producto", "productos", "principal"].forEach((k) => clienteQuery.invalidateQueries({ queryKey: [k] }));
      navegar(`/pedidos/${pedido.id_pedido}`, { replace: true, state: { pedido, recienCreado: true } });
    } catch (e) {
      setEnviando(false);
      if (e.codigo === "articulos_no_disponibles") {
        await clienteQuery.invalidateQueries({ queryKey: CLAVE_CARRITO });
        avisar("Algunos artículos cambiaron de disponibilidad. Revisa tu carrito.", { tipo: "error", duracion: 6000 });
        navegar("/carrito");
      } else if (e.codigo === "carrito_vacio") {
        await clienteQuery.invalidateQueries({ queryKey: CLAVE_CARRITO });
        setError("Tu carrito ya no tiene artículos. Si confirmaste el pedido en otra pestaña, ya quedó registrado.");
      } else if (e.codigo === "direccion_no_encontrada") {
        await clienteQuery.invalidateQueries({ queryKey: CLAVE_DIRECCIONES });
        setPaso(0);
        setError("La dirección elegida ya no existe. Elige otra.");
      } else if (e.codigo === "validacion") {
        setError(Object.values(e.campos)[0] ?? e.message);
      } else {
        setError(e.message);
      }
    }
  };

  return (
    <div className={`contenedor ${s.pagina}`}>
      <h1 className={s.titulo}>Registrar pedido</h1>

      <ol className={s.pasos} aria-label="Pasos del pedido">
        {PASOS.map((nombre, i) => (
          <li key={nombre} className={`${s.paso} ${i <= paso ? s.pasoHecho : ""}`} aria-current={i === paso ? "step" : undefined}>
            <span className={s.numero}>{i < paso ? <Check size={14} /> : i + 1}</span>
            {nombre}
          </li>
        ))}
        <span className={s.progreso} aria-hidden>
          <motion.span className={s.progresoRelleno} animate={{ scaleX: paso / (PASOS.length - 1) }} transition={{ type: "spring", stiffness: 200, damping: 30 }} />
        </span>
      </ol>

      <div className={s.rejilla}>
        <div>
          <AnimatePresence mode="wait" initial={false}>
            {paso === 0 ? (
              <motion.section key="entrega" className={s.panel} initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.28 }}>
                <h2 className={s.subtitulo}>¿Dónde lo entregamos?</h2>
                {error && <p className={s.error} role="alert">{error}</p>}
                {direcciones.length === 0 ? (
                  <EstadoVacio icono={MapPin} titulo="Agrega una dirección de entrega" accion={<Boton icono={Plus} onClick={() => setNueva(true)}>Agregar dirección</Boton>}>
                    Necesitamos una dirección para enviarte el pedido.
                  </EstadoVacio>
                ) : (
                  <div className={s.direcciones} role="radiogroup" aria-label="Dirección de entrega">
                    {direcciones.map((d) => {
                      const elegida = d.id_direccion === idDireccion;
                      return (
                        <button key={d.id_direccion} type="button" role="radio" aria-checked={elegida} className={`${s.direccion} ${elegida ? s.direccionElegida : ""}`} onClick={() => setIdDireccion(d.id_direccion)}>
                          <span className={s.radio} aria-hidden>
                            {elegida && <motion.span layoutId="radio-direccion" className={s.radioPunto} />}
                          </span>
                          <span className={s.textoDireccion}>
                            <strong>{d.direccion}</strong>
                            {d.complemento && <span>{d.complemento}</span>}
                            <span>{textoDireccion(d)}</span>
                          </span>
                          {d.principal && <span className={s.insignia}>Principal</span>}
                        </button>
                      );
                    })}
                    <button type="button" className={s.otra} onClick={() => setNueva(true)}>
                      <Plus size={18} aria-hidden /> Usar otra dirección
                    </button>
                  </div>
                )}
                <Campo etiqueta="Observaciones para la entrega" multilinea maxLength={1000} contador={1000} ayuda="Opcional. Ej.: llamar antes de entregar" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
                <div className={s.botones}>
                  <Boton variante="fantasma" to="/carrito">
                    Volver al carrito
                  </Boton>
                  <Boton tamano="lg" onClick={() => { setError(null); setPaso(1); }} disabled={!direccion}>
                    Revisar pedido
                  </Boton>
                </div>
              </motion.section>
            ) : (
              <motion.section key="revision" className={s.panel} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }} transition={{ duration: 0.28 }}>
                <h2 className={s.subtitulo}>Revisa y confirma</h2>
                <div className={s.resumenEntrega}>
                  <div>
                    <p className={s.etiqueta}>Entrega en</p>
                    <p>
                      <strong>{direccion?.direccion}</strong>
                      {direccion?.complemento && `, ${direccion.complemento}`}
                    </p>
                    <p className={s.tenue}>{direccion && textoDireccion(direccion)}</p>
                    {observaciones.trim() && <p className={s.tenue}>Observaciones: {observaciones.trim()}</p>}
                  </div>
                  <Boton tamano="sm" variante="secundario" onClick={() => setPaso(0)} disabled={enviando}>
                    Cambiar
                  </Boton>
                </div>
                {error && <p className={s.error} role="alert">{error}</p>}
                <p className={s.tenue}>Al confirmar, reservamos las unidades de tu carrito y el pedido queda pendiente de verificación por nuestro equipo.</p>
                <div className={s.botones}>
                  <Boton variante="fantasma" onClick={() => setPaso(0)} disabled={enviando}>
                    Atrás
                  </Boton>
                  <Boton tamano="lg" variante="acento" onClick={confirmar} cargando={enviando}>
                    {enviando ? "Registrando pedido…" : `Confirmar pedido por ${formatoCOP(carrito.total)}`}
                  </Boton>
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </div>

        <aside className={s.resumen} aria-label="Artículos del pedido">
          <h2 className={s.subtitulo}>{plural(carrito.cantidad_unidades, "unidad", "unidades")}</h2>
          <ul className={s.items}>
            {carrito.items.map((item) => (
              <li key={item.id_detalle_carrito} className={s.item}>
                <span className={s.miniatura}>
                  <ImagenProducto src={item.imagen} nombre={item.nombre} marca={item.marca} categoria={item.categoria} tamano="sm" />
                  <span className={`${s.cantidad} numero`}>{item.cantidad}</span>
                </span>
                <span className={s.itemTexto}>
                  <strong>{item.nombre}</strong>
                  <span>{describirVariante(item)}</span>
                </span>
                <span className="numero">{formatoCOP(item.subtotal)}</span>
              </li>
            ))}
          </ul>
          <div className={s.total}>
            <span>Total</span>
            <strong className="numero">{formatoCOP(carrito.total)}</strong>
          </div>
        </aside>
      </div>

      <FormularioDireccion abierto={nueva} alCerrar={() => setNueva(false)} alGuardar={(d) => d && setIdDireccion(d.id_direccion)} />
    </div>
  );
}
