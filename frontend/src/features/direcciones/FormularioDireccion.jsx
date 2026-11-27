import { AlertTriangle } from "lucide-react";

import useFormulario from "../../hooks/useFormulario";
import Campo from "../../components/ui/Campo";
import Boton from "../../components/ui/Boton";
import Modal from "../../components/ui/Modal";
import { useAvisos } from "../../components/ui/Avisos";
import { validarDireccion } from "../../utils/validacion";
import { useActualizarDireccion, useCrearDireccion } from "./useDirecciones";
import s from "./Direcciones.module.css";

const CAMPOS = ["departamento", "municipio", "direccion", "complemento", "codigo_postal"];

/** Alta o edición de una dirección en ventana modal. */
export default function FormularioDireccion({ abierto, alCerrar, direccion = null, alGuardar }) {
  return (
    <Modal abierto={abierto} alCerrar={alCerrar} titulo={direccion ? "Editar dirección" : "Nueva dirección"} ancho="600px">
      {abierto && <Contenido direccion={direccion} alCerrar={alCerrar} alGuardar={alGuardar} />}
    </Modal>
  );
}

function Contenido({ direccion, alCerrar, alGuardar }) {
  const { avisar } = useAvisos();
  const crear = useCrearDireccion();
  const actualizar = useActualizarDireccion();
  const inicial = Object.fromEntries(CAMPOS.map((c) => [c, direccion?.[c] ?? ""]));
  const form = useFormulario({ ...inicial, principal: direccion?.principal ?? false }, validarDireccion);
  const guardando = crear.isPending || actualizar.isPending;

  const enviar = (e) => {
    e.preventDefault();
    form.setErrorGeneral(null);
    if (!form.validarTodo()) return;

    const limpio = Object.fromEntries(CAMPOS.map((c) => [c, form.valores[c].trim() || null]));
    const opciones = {
      onSuccess: (datos) => {
        avisar(direccion ? "Dirección actualizada." : "Dirección agregada.");
        alGuardar?.(datos?.direccion);
        alCerrar();
      },
      onError: (error) => form.aplicarErrorApi(error),
    };

    if (direccion) {
      // PATCH parcial: solo lo que cambió.
      const cambios = Object.fromEntries(Object.entries(limpio).filter(([c, valor]) => valor !== (direccion[c] ?? null)));
      if (form.valores.principal && !direccion.principal) cambios.principal = true;
      if (!Object.keys(cambios).length) {
        alCerrar();
        return;
      }
      actualizar.mutate({ id: direccion.id_direccion, cambios }, opciones);
    } else {
      crear.mutate({ ...limpio, principal: form.valores.principal }, opciones);
    }
  };

  return (
    <form className={s.formulario} onSubmit={enviar} noValidate>
      {form.errorGeneral && (
        <div className={s.alerta} role="alert">
          <AlertTriangle size={18} aria-hidden /> {form.errorGeneral}
        </div>
      )}
      <div className={s.dos}>
        <Campo etiqueta="Departamento" required maxLength={60} autoComplete="address-level1" {...form.campo("departamento")} />
        <Campo etiqueta="Municipio" required maxLength={80} autoComplete="address-level2" {...form.campo("municipio")} />
      </div>
      <Campo etiqueta="Dirección" required maxLength={150} autoComplete="address-line1" ayuda="Ej.: Calle 26 # 30-15" {...form.campo("direccion")} />
      <Campo etiqueta="Complemento" maxLength={100} autoComplete="address-line2" ayuda="Opcional. Apartamento, barrio, referencias" {...form.campo("complemento")} />
      <Campo etiqueta="Código postal" maxLength={10} inputMode="numeric" autoComplete="postal-code" ayuda="Opcional. De 4 a 10 dígitos" {...form.campo("codigo_postal")} />
      {!direccion?.principal && (
        <label className={s.interruptor}>
          <input type="checkbox" checked={form.valores.principal} onChange={(e) => form.cambiar("principal", e.target.checked)} />
          <span className={s.pista} aria-hidden />
          Usar como dirección principal
        </label>
      )}
      <div className={s.botones}>
        <Boton type="button" variante="fantasma" onClick={alCerrar}>
          Cancelar
        </Boton>
        <Boton type="submit" cargando={guardando}>
          {direccion ? "Guardar cambios" : "Agregar dirección"}
        </Boton>
      </div>
    </form>
  );
}
