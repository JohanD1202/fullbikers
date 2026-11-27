import { ShoppingBag, ServerCrash } from "lucide-react";

import { useCarrito } from "../features/carrito/useCarrito";
import ListaCarrito from "../features/carrito/ListaCarrito";
import Boton from "../components/ui/Boton";
import EstadoVacio from "../components/ui/EstadoVacio";
import Esqueleto from "../components/ui/Esqueleto";
import { formatoCOP, plural } from "../utils/format";
import s from "./CarritoPage.module.css";

export default function CarritoPage() {
  const { data: carrito, isPending, isError, error, refetch } = useCarrito();

  return (
    <div className={`contenedor ${s.pagina}`}>
      <h1 className={s.titulo}>Tu carrito</h1>

      {isPending ? (
        <div className={s.rejilla}>
          <div className={s.lineas}>
            {[0, 1, 2].map((i) => (
              <Esqueleto key={i} alto="120px" radio="var(--r-superficie)" />
            ))}
          </div>
          <Esqueleto alto="220px" radio="var(--r-contenedor)" />
        </div>
      ) : isError ? (
        <EstadoVacio icono={ServerCrash} tono="error" titulo="No pudimos cargar el carrito" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
          {error.message}
        </EstadoVacio>
      ) : carrito.vacio ? (
        <EstadoVacio icono={ShoppingBag} titulo="Tu carrito está vacío" accion={<Boton to="/productos">Explorar el catálogo</Boton>}>
          Agrega productos desde el catálogo para preparar tu pedido.
        </EstadoVacio>
      ) : (
        <div className={s.rejilla}>
          <div className={s.lineas}>
            <ListaCarrito carrito={carrito} />
          </div>
          <aside className={s.resumen} aria-label="Resumen del carrito">
            <h2 className={s.tituloResumen}>Resumen</h2>
            <dl className={s.cifras}>
              <div>
                <dt>Artículos</dt>
                <dd className="numero">{plural(carrito.cantidad_unidades, "unidad", "unidades")}</dd>
              </div>
              <div className={s.total}>
                <dt>Total</dt>
                <dd className="numero">{formatoCOP(carrito.total)}</dd>
              </div>
            </dl>
            <p className={s.nota}>Precios vigentes del catálogo. Las existencias se confirman al registrar el pedido.</p>
            {!carrito.todos_disponibles && (
              <p className={s.alerta} role="status">
                Hay artículos marcados que no se pueden comprar ahora. Retíralos o ajusta la cantidad para continuar.
              </p>
            )}
            {carrito.todos_disponibles ? (
              <Boton tamano="lg" variante="acento" to="/pedido" className={s.continuar}>
                Continuar con el pedido
              </Boton>
            ) : (
              <Boton tamano="lg" variante="acento" disabled className={s.continuar}>
                Continuar con el pedido
              </Boton>
            )}
            <Boton variante="fantasma" to="/productos" className={s.continuar}>
              Seguir comprando
            </Boton>
          </aside>
        </div>
      )}
    </div>
  );
}
