// Detalle de producto con variantes activas (RF-05) y alta en el carrito (RF-12).
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, Check, PackageX, ServerCrash, ShoppingBag, Truck } from "lucide-react";

import { catalogoApi } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { puedeComprar } from "../utils/roles";
import { describirVariante, formatoCOP } from "../utils/format";
import { useAgregarAlCarrito } from "../features/carrito/useCarrito";
import { useCajonCarrito } from "../features/carrito/CajonCarrito";
import ImagenProducto from "../components/ui/ImagenProducto";
import SelectorCantidad from "../components/ui/SelectorCantidad";
import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";
import Esqueleto from "../components/ui/Esqueleto";
import { useAvisos } from "../components/ui/Avisos";
import s from "./ProductoPage.module.css";

export default function ProductoPage() {
  const { id } = useParams();
  const idValido = /^\d+$/.test(id ?? "");
  const { data: producto, isPending, isError, error, refetch } = useQuery({
    queryKey: ["producto", id],
    queryFn: () => catalogoApi.producto(id),
    enabled: idValido,
    retry: (n, e) => e?.status !== 404 && n < 2,
  });

  if (!idValido || error?.status === 404) {
    return (
      <div className="contenedor">
        <EstadoVacio icono={PackageX} titulo="Este producto no está disponible" accion={<Boton to="/productos">Volver al catálogo</Boton>}>
          Puede que se haya retirado del catálogo o que el enlace no sea correcto.
        </EstadoVacio>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="contenedor">
        <EstadoVacio icono={ServerCrash} tono="error" titulo="No pudimos cargar el producto" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
          {error.message}
        </EstadoVacio>
      </div>
    );
  }
  if (isPending) return <EsqueletoProducto />;
  return <DetalleProducto key={producto.id_producto} producto={producto} />;
}

function DetalleProducto({ producto }) {
  const { usuario } = useAuth();
  const comprador = puedeComprar(usuario);
  const { avisar } = useAvisos();
  const { abrir } = useCajonCarrito();
  const agregar = useAgregarAlCarrito();

  const variantes = producto.variantes;
  const unica = variantes.length === 1 && describirVariante(variantes[0]) === "Única";
  const primeraDisponible = useMemo(() => variantes.find((v) => v.disponible) ?? null, [variantes]);
  const [idVariante, setIdVariante] = useState(primeraDisponible?.id_variante ?? null);
  const [cantidad, setCantidad] = useState(1);
  const [agregado, setAgregado] = useState(false);
  const [errorStock, setErrorStock] = useState(null);

  const variante = variantes.find((v) => v.id_variante === idVariante) ?? null;

  useEffect(() => {
    setCantidad(1);
    setErrorStock(null);
  }, [idVariante]);

  const enviar = () => {
    if (!variante) return;
    setErrorStock(null);
    agregar.mutate(
      { id_producto: producto.id_producto, id_variante: variante.id_variante, cantidad },
      {
        onSuccess: () => {
          setAgregado(true);
          window.setTimeout(() => setAgregado(false), 1800);
          avisar(`Agregaste ${cantidad} × ${producto.nombre} al carrito.`);
          abrir();
        },
        onError: (e) => {
          if (e.codigo === "stock_insuficiente") {
            const disponible = e.detalles?.stock_disponible;
            const enCarrito = e.detalles?.cantidad_en_carrito;
            setErrorStock(
              enCarrito
                ? `Ya tienes ${enCarrito} en el carrito y solo hay ${disponible} disponibles.`
                : `Solo hay ${disponible} unidades disponibles.`
            );
          } else {
            avisar(e.message, { tipo: "error" });
          }
        },
      }
    );
  };

  return (
    <div className={`contenedor ${s.pagina}`}>
      <Link to="/productos" className={s.volver}>
        <ArrowLeft size={18} aria-hidden /> Catálogo
      </Link>

      <div className={s.rejilla}>
        <motion.div
          className={s.foto}
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          <ImagenProducto
            src={producto.imagen}
            nombre={producto.nombre}
            referencia={producto.referencia}
            marca={producto.marca}
            categoria={producto.categoria}
            tamano="lg"
          />
        </motion.div>

        <div className={s.info}>
          <p className={s.migas}>
            <Link to={`/productos?categoria=${producto.id_categoria}`}>{producto.categoria}</Link>
            {producto.marca && <span>{producto.marca}</span>}
          </p>
          <h1 className={s.nombre}>{producto.nombre}</h1>
          <p className={`${s.precio} numero`}>{formatoCOP(producto.precio)}</p>
          {producto.descripcion && <p className={s.descripcion}>{producto.descripcion}</p>}

          {!unica && (
            <fieldset className={s.variantes}>
              <legend>Elige tu opción</legend>
              <div className={s.opciones} role="radiogroup" aria-label="Opciones del producto">
                {variantes.map((v) => {
                  const elegida = v.id_variante === idVariante;
                  return (
                    <button
                      key={v.id_variante}
                      type="button"
                      role="radio"
                      aria-checked={elegida}
                      disabled={!v.disponible}
                      className={`${s.opcion} ${elegida ? s.opcionElegida : ""}`}
                      onClick={() => setIdVariante(v.id_variante)}
                    >
                      {elegida && <motion.span layoutId="variante-elegida" className={s.fondoOpcion} transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
                      <span className={s.textoOpcion}>{describirVariante(v)}</span>
                      {!v.disponible && <span className={s.textoOpcion}>Agotada</span>}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}

          <AnimatePresence mode="wait">
            {variante ? (
              <motion.p
                key={variante.id_variante}
                className={s.stock}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
              >
                <span className={`${s.punto} ${variante.stock <= 5 ? s.puntoBajo : ""}`} aria-hidden />
                {variante.stock <= 5 ? `Quedan ${variante.stock} unidades` : "Disponible"}
                <span className={s.sku}>SKU {variante.sku}</span>
              </motion.p>
            ) : (
              <p className={s.stock}>
                <span className={`${s.punto} ${s.puntoAgotado}`} aria-hidden /> Sin existencias por ahora
              </p>
            )}
          </AnimatePresence>

          {comprador ? (
            <div className={s.compra}>
              <SelectorCantidad valor={cantidad} alCambiar={setCantidad} max={variante?.stock ?? 1} deshabilitado={!variante || agregar.isPending} />
              <Boton tamano="lg" variante="acento" className={s.agregar} onClick={enviar} disabled={!variante} cargando={agregar.isPending} icono={agregado ? Check : ShoppingBag}>
                {agregado ? "Agregado" : "Agregar al carrito"}
              </Boton>
            </div>
          ) : (
            <div className={s.consulta}>
              <strong>Vista de consulta</strong>
              <p>Tu rol puede consultar productos y existencias, pero no comprar.</p>
              <ul className={s.tablaStock}>
                {variantes.map((v) => (
                  <li key={v.id_variante}>
                    <span>
                      {describirVariante(v)} <small>{v.sku}</small>
                    </span>
                    <strong className="numero">{v.stock} u.</strong>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <AnimatePresence>
            {errorStock && (
              <motion.p className={s.error} role="alert" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                {errorStock}
              </motion.p>
            )}
          </AnimatePresence>

          <p className={s.envio}>
            <Truck size={18} aria-hidden /> Envíos a toda Colombia desde Tuluá.
          </p>
        </div>
      </div>
    </div>
  );
}

function EsqueletoProducto() {
  return (
    <div className={`contenedor ${s.pagina}`} aria-busy="true">
      <Esqueleto alto="1rem" ancho="90px" />
      <div className={s.rejilla} style={{ marginTop: "1.5rem" }}>
        <Esqueleto alto="auto" className={s.foto} radio="var(--r-contenedor)" />
        <div className={s.info}>
          <Esqueleto alto="1rem" ancho="30%" />
          <Esqueleto alto="2.6rem" ancho="85%" />
          <Esqueleto alto="2rem" ancho="40%" />
          <Esqueleto alto="4rem" />
          <Esqueleto alto="3rem" ancho="70%" radio="999px" />
        </div>
      </div>
    </div>
  );
}
