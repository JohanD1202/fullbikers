import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { ShoppingBag } from "lucide-react";

import Modal from "../../components/ui/Modal";
import Boton from "../../components/ui/Boton";
import EstadoVacio from "../../components/ui/EstadoVacio";
import Esqueleto from "../../components/ui/Esqueleto";
import { formatoCOP, plural } from "../../utils/format";
import { useCarrito } from "./useCarrito";
import ListaCarrito from "./ListaCarrito";
import s from "./CajonCarrito.module.css";

const CajonContext = createContext(null);

export function CajonCarritoProvider({ children }) {
  const [abierto, setAbierto] = useState(false);
  const abrir = useCallback(() => setAbierto(true), []);
  const cerrar = useCallback(() => setAbierto(false), []);
  const valor = useMemo(() => ({ abierto, abrir, cerrar }), [abierto, abrir, cerrar]);
  return (
    <CajonContext.Provider value={valor}>
      {children}
      <CajonCarrito abierto={abierto} alCerrar={cerrar} />
    </CajonContext.Provider>
  );
}

export function useCajonCarrito() {
  return useContext(CajonContext) ?? { abierto: false, abrir: () => {}, cerrar: () => {} };
}

function CajonCarrito({ abierto, alCerrar }) {
  const { data: carrito, isPending, isError, error, refetch } = useCarrito();

  const pie =
    carrito && !carrito.vacio ? (
      <div className={s.pie}>
        <div className={s.total}>
          <span>Total</span>
          <strong className="numero">{formatoCOP(carrito.total)}</strong>
        </div>
        {!carrito.todos_disponibles && <p className={s.alerta}>Retire o ajuste los artículos marcados para continuar.</p>}
        <div className={s.acciones}>
          <Boton variante="secundario" to="/carrito" onClick={alCerrar}>
            Ver carrito
          </Boton>
          {carrito.todos_disponibles ? (
            <Boton variante="acento" to="/pedido" onClick={alCerrar}>
              Continuar con el pedido
            </Boton>
          ) : (
            <Boton variante="acento" disabled>
              Continuar con el pedido
            </Boton>
          )}
        </div>
      </div>
    ) : null;

  return (
    <Modal
      abierto={abierto}
      alCerrar={alCerrar}
      lado="derecha"
      titulo={carrito && !carrito.vacio ? `Tu carrito (${plural(carrito.cantidad_unidades, "unidad", "unidades")})` : "Tu carrito"}
      pie={pie}
    >
      {isPending ? (
        <div className={s.cargando}>
          {[0, 1, 2].map((i) => (
            <Esqueleto key={i} alto="88px" radio="18px" />
          ))}
        </div>
      ) : isError ? (
        <EstadoVacio titulo="No pudimos cargar el carrito" tono="error" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
          {error.message}
        </EstadoVacio>
      ) : carrito.vacio ? (
        <EstadoVacio
          icono={ShoppingBag}
          titulo="Tu carrito está vacío"
          accion={
            <Boton to="/productos" onClick={alCerrar}>
              Explorar el catálogo
            </Boton>
          }
        >
          Agrega cascos, guantes o accesorios y aparecerán aquí.
        </EstadoVacio>
      ) : (
        <ListaCarrito carrito={carrito} compacto alNavegar={alCerrar} />
      )}
    </Modal>
  );
}
