// Detalle de un pedido propio y su estado actual (RF-19, API.md §9).
import { useLocation, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Check, PackageSearch, ServerCrash, XCircle } from "lucide-react";

import { pedidosApi } from "../api/endpoints";
import ImagenProducto from "../components/ui/ImagenProducto";
import LineaVial from "../components/ui/LineaVial";
import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";
import PantallaCarga from "../components/ui/PantallaCarga";
import { describirVariante, formatoCOP, formatoFecha, plural } from "../utils/format";
import s from "./PedidoPage.module.css";

// Estados de backend/models/pedido.py, en el orden del flujo.
const FLUJO = [
  { estado: "pendiente", nombre: "Pendiente", texto: "Recibimos tu pedido" },
  { estado: "confirmado", nombre: "Confirmado", texto: "Verificado por nuestro equipo" },
  { estado: "en_preparacion", nombre: "En preparación", texto: "Empacando tu equipo" },
  { estado: "enviado", nombre: "Enviado", texto: "Va en camino" },
  { estado: "entregado", nombre: "Entregado", texto: "Llegó a su destino" },
];

export default function PedidoPage() {
  const { id } = useParams();
  const { state } = useLocation();
  const idValido = /^\d+$/.test(id ?? "");
  const inicial = state?.pedido?.id_pedido === Number(id) ? state.pedido : undefined;

  const { data: pedido, isPending, isError, error, refetch } = useQuery({
    queryKey: ["pedido", id],
    queryFn: async () => (await pedidosApi.obtener(id)).pedido,
    enabled: idValido,
    initialData: inicial,
    retry: (n, e) => e?.status !== 404 && n < 2,
  });

  if (!idValido || error?.status === 404) {
    return (
      <div className="contenedor">
        <EstadoVacio icono={PackageSearch} titulo="No encontramos este pedido" accion={<Boton to="/">Ir al inicio</Boton>}>
          Revisa el número del pedido. Solo puedes consultar pedidos de tu cuenta.
        </EstadoVacio>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="contenedor">
        <EstadoVacio icono={ServerCrash} tono="error" titulo="No pudimos cargar el pedido" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
          {error.message}
        </EstadoVacio>
      </div>
    );
  }
  if (isPending) return <PantallaCarga mensaje="Cargando tu pedido…" />;

  const recien = Boolean(state?.recienCreado);
  const cancelado = pedido.estado === "cancelado";
  const indice = FLUJO.findIndex((f) => f.estado === pedido.estado);
  const e = pedido.entrega;

  return (
    <div className={`contenedor ${s.pagina}`}>
      <header className={`${s.cabecera} ${recien ? s.celebracion : ""}`}>
        {recien && <LineaVial className={s.via} grosor={16} demora={0.1} />}
        <div className={s.cabeceraTexto}>
          <p className={s.fecha}>{formatoFecha(pedido.fecha)}</p>
          <h1 className={s.titulo}>{recien ? `¡Listo! Registramos tu pedido #${pedido.id_pedido}` : `Pedido #${pedido.id_pedido}`}</h1>
          {recien && <p className={s.lema}>Nuestro equipo lo verificará y te contactará para coordinar la entrega.</p>}
        </div>
      </header>

      <div className={s.rejilla}>
        <section className={s.panel} aria-labelledby="estado">
          <h2 id="estado" className={s.subtitulo}>
            Estado
          </h2>
          {cancelado ? (
            <p className={s.cancelado}>
              <XCircle size={20} aria-hidden /> Este pedido fue cancelado.
            </p>
          ) : (
            <ol className={s.linea}>
              {FLUJO.map((f, i) => {
                const hecho = i <= indice;
                const actual = i === indice;
                return (
                  <motion.li
                    key={f.estado}
                    className={`${s.hito} ${hecho ? s.hecho : ""} ${actual ? s.actual : ""}`}
                    aria-current={actual ? "step" : undefined}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.15 + i * 0.08 }}
                  >
                    <span className={s.marca}>{hecho && !actual ? <Check size={14} /> : null}</span>
                    <span>
                      <strong>{f.nombre}</strong>
                      <small>{f.texto}</small>
                    </span>
                  </motion.li>
                );
              })}
            </ol>
          )}
          {pedido.fecha_actualizacion && pedido.fecha_actualizacion !== pedido.fecha && (
            <p className={s.tenue}>Última actualización: {formatoFecha(pedido.fecha_actualizacion)}</p>
          )}

          <h2 className={s.subtitulo}>Entrega</h2>
          <address className={s.direccion}>
            <strong>{e.direccion}</strong>
            {e.complemento && <span>{e.complemento}</span>}
            <span>{[e.municipio, e.departamento, e.codigo_postal].filter(Boolean).join(", ")}</span>
          </address>
          {pedido.observaciones && (
            <>
              <h2 className={s.subtitulo}>Observaciones</h2>
              <p className={s.tenue}>{pedido.observaciones}</p>
            </>
          )}
        </section>

        <section className={s.panel} aria-labelledby="articulos">
          <h2 id="articulos" className={s.subtitulo}>
            {plural(pedido.cantidad_unidades, "unidad", "unidades")}
          </h2>
          <ul className={s.items}>
            {pedido.detalles.map((d) => (
              <li key={d.id_detalle} className={s.item}>
                <span className={s.miniatura}>
                  <ImagenProducto src={d.imagen} nombre={d.nombre} referencia={d.referencia} tamano="sm" />
                </span>
                <span className={s.itemTexto}>
                  <strong>{d.nombre}</strong>
                  <span>
                    {describirVariante(d)}, {d.cantidad} × {formatoCOP(d.precio_unitario)}
                  </span>
                </span>
                <strong className="numero">{formatoCOP(d.subtotal)}</strong>
              </li>
            ))}
          </ul>
          <dl className={s.cifras}>
            <div>
              <dt>Subtotal</dt>
              <dd className="numero">{formatoCOP(pedido.subtotal)}</dd>
            </div>
            <div className={s.total}>
              <dt>Total</dt>
              <dd className="numero">{formatoCOP(pedido.total)}</dd>
            </div>
          </dl>
          <p className={s.tenue}>Precios del momento de la compra.</p>
          <Boton variante="secundario" to="/productos">
            Seguir comprando
          </Boton>
        </section>
      </div>
    </div>
  );
}
