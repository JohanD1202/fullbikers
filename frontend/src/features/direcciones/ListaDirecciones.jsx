import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { MapPin, Pencil, Plus, Star, Trash2 } from "lucide-react";

import Boton from "../../components/ui/Boton";
import Modal from "../../components/ui/Modal";
import Esqueleto from "../../components/ui/Esqueleto";
import EstadoVacio from "../../components/ui/EstadoVacio";
import { useAvisos } from "../../components/ui/Avisos";
import { useActualizarDireccion, useDirecciones, useEliminarDireccion } from "./useDirecciones";
import FormularioDireccion from "./FormularioDireccion";
import s from "./Direcciones.module.css";

export function textoDireccion(d) {
  return [d.municipio, d.departamento, d.codigo_postal].filter(Boolean).join(", ");
}

/** Gestión completa de direcciones: listar, agregar, editar, principal y eliminar. */
export default function ListaDirecciones() {
  const { data: direcciones, isPending, isError, error, refetch } = useDirecciones();
  const { avisar } = useAvisos();
  const actualizar = useActualizarDireccion();
  const eliminar = useEliminarDireccion();
  const [formulario, setFormulario] = useState({ abierto: false, direccion: null });
  const [porEliminar, setPorEliminar] = useState(null);

  if (isPending) {
    return (
      <div className={s.lista}>
        <Esqueleto alto="170px" radio="var(--r-superficie)" />
        <Esqueleto alto="170px" radio="var(--r-superficie)" />
      </div>
    );
  }
  if (isError) {
    return (
      <EstadoVacio tono="error" titulo="No pudimos cargar tus direcciones" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
        {error.message}
      </EstadoVacio>
    );
  }

  const marcarPrincipal = (d) =>
    actualizar.mutate(
      { id: d.id_direccion, cambios: { principal: true } },
      { onSuccess: () => avisar("Dirección principal actualizada."), onError: (e) => avisar(e.message, { tipo: "error" }) }
    );

  const confirmarEliminar = () =>
    eliminar.mutate(porEliminar.id_direccion, {
      onSuccess: () => {
        avisar("Dirección eliminada.");
        setPorEliminar(null);
      },
      onError: (e) => {
        avisar(e.message, { tipo: "error" });
        setPorEliminar(null);
      },
    });

  return (
    <>
      {direcciones.length === 0 ? (
        <EstadoVacio icono={MapPin} titulo="Aún no tienes direcciones" accion={<Boton icono={Plus} onClick={() => setFormulario({ abierto: true, direccion: null })}>Agregar dirección</Boton>}>
          Agrega una dirección de entrega para poder registrar pedidos.
        </EstadoVacio>
      ) : (
        <ul className={s.lista}>
          <AnimatePresence initial={false}>
            {direcciones.map((d) => (
              <motion.li
                key={d.id_direccion}
                layout
                className={`${s.tarjeta} ${d.principal ? s.principal : ""}`}
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
              >
                {d.principal && (
                  <span className={s.insignia}>
                    <Star size={12} aria-hidden fill="currentColor" /> Principal
                  </span>
                )}
                <p className={s.lineaPrincipal}>{d.direccion}</p>
                {d.complemento && <p className={s.secundario}>{d.complemento}</p>}
                <p className={s.secundario}>{textoDireccion(d)}</p>
                <div className={s.accionesTarjeta}>
                  {!d.principal && (
                    <Boton tamano="sm" variante="secundario" onClick={() => marcarPrincipal(d)} cargando={actualizar.isPending && actualizar.variables?.id === d.id_direccion}>
                      Usar como principal
                    </Boton>
                  )}
                  <Boton tamano="sm" variante="fantasma" icono={Pencil} onClick={() => setFormulario({ abierto: true, direccion: d })} aria-label={`Editar ${d.direccion}`}>
                    Editar
                  </Boton>
                  <Boton tamano="sm" variante="fantasma" icono={Trash2} onClick={() => setPorEliminar(d)} aria-label={`Eliminar ${d.direccion}`}>
                    Eliminar
                  </Boton>
                </div>
              </motion.li>
            ))}
            <motion.li key="agregar" layout>
              <button type="button" className={s.agregar} style={{ width: "100%" }} onClick={() => setFormulario({ abierto: true, direccion: null })}>
                <Plus size={22} aria-hidden />
                Agregar dirección
              </button>
            </motion.li>
          </AnimatePresence>
        </ul>
      )}

      <FormularioDireccion abierto={formulario.abierto} direccion={formulario.direccion} alCerrar={() => setFormulario({ abierto: false, direccion: null })} />

      <Modal
        abierto={Boolean(porEliminar)}
        alCerrar={() => setPorEliminar(null)}
        titulo="¿Eliminar esta dirección?"
        ancho="460px"
        pie={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
            <Boton variante="fantasma" onClick={() => setPorEliminar(null)}>
              Conservar
            </Boton>
            <Boton variante="peligro" onClick={confirmarEliminar} cargando={eliminar.isPending}>
              Eliminar dirección
            </Boton>
          </div>
        }
      >
        {porEliminar && (
          <p>
            <strong>{porEliminar.direccion}</strong>, {textoDireccion(porEliminar)}. Los pedidos que ya hiciste a esta dirección no cambian.
            {porEliminar.principal && " Era tu dirección principal: elige otra después."}
          </p>
        )}
      </Modal>
    </>
  );
}
