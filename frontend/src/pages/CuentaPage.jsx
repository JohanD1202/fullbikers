// Mi cuenta: datos personales (RF-10) y direcciones (RF-11).
// Empleado: solo consulta (/auth/me); la API le responde 403 en /perfil y /direcciones.
import { useState } from "react";
import { AlertTriangle } from "lucide-react";

import { perfilApi } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import useFormulario from "../hooks/useFormulario";
import Campo from "../components/ui/Campo";
import Boton from "../components/ui/Boton";
import { useAvisos } from "../components/ui/Avisos";
import ListaDirecciones from "../features/direcciones/ListaDirecciones";
import { validarPersona } from "../utils/validacion";
import { NOMBRE_ROL, puedeComprar } from "../utils/roles";
import s from "./CuentaPage.module.css";

const CAMPOS = ["nombre", "apellido", "correo", "telefono"];

export default function CuentaPage() {
  const { usuario } = useAuth();
  const comprador = puedeComprar(usuario);

  return (
    <div className={`contenedor ${s.pagina}`}>
      <header className={s.cabecera}>
        <span className={s.avatar} aria-hidden>
          {`${usuario.nombre[0] ?? ""}${usuario.apellido[0] ?? ""}`.toUpperCase()}
        </span>
        <div>
          <h1 className={s.titulo}>
            {usuario.nombre} {usuario.apellido}
          </h1>
          <p className={s.rol}>{NOMBRE_ROL[usuario.rol] ?? usuario.rol}</p>
        </div>
      </header>

      <section className={s.seccion} aria-labelledby="datos">
        <div className={s.intro}>
          <h2 id="datos" className={s.subtitulo}>
            Datos personales
          </h2>
          <p>{comprador ? "Así te contactamos sobre tus pedidos." : "Tu información de acceso. Para modificarla, contacta al administrador."}</p>
        </div>
        {comprador ? <FormularioPerfil /> : <DatosSoloLectura usuario={usuario} />}
      </section>

      {comprador && (
        <section className={s.seccion} aria-labelledby="direcciones">
          <div className={s.intro}>
            <h2 id="direcciones" className={s.subtitulo}>
              Direcciones de entrega
            </h2>
            <p>La dirección principal aparece preseleccionada al registrar un pedido.</p>
          </div>
          <ListaDirecciones />
        </section>
      )}
    </div>
  );
}

function DatosSoloLectura({ usuario }) {
  return (
    <dl className={s.lectura}>
      {[
        ["Nombre", `${usuario.nombre} ${usuario.apellido}`],
        ["Correo electrónico", usuario.correo],
        ["Teléfono", usuario.telefono || "Sin teléfono"],
      ].map(([t, v]) => (
        <div key={t}>
          <dt>{t}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function FormularioPerfil() {
  const { usuario, actualizarUsuario } = useAuth();
  const { avisar } = useAvisos();
  const [guardando, setGuardando] = useState(false);
  const inicial = Object.fromEntries(CAMPOS.map((c) => [c, usuario[c] ?? ""]));
  const form = useFormulario(inicial, validarPersona);

  // Solo se envían los campos que cambiaron (PATCH parcial, API.md §6).
  const cambios = Object.fromEntries(
    CAMPOS.map((c) => [c, form.valores[c].trim()]).filter(([c, valor]) => valor !== (usuario[c] ?? ""))
  );
  if ("correo" in cambios && cambios.correo.toLowerCase() === usuario.correo) delete cambios.correo;
  const hayCambios = Object.keys(cambios).length > 0;

  const enviar = async (e) => {
    e.preventDefault();
    form.setErrorGeneral(null);
    if (!hayCambios || !form.validarTodo()) return;
    setGuardando(true);
    try {
      const cuerpo = { ...cambios };
      if ("telefono" in cuerpo && !cuerpo.telefono) cuerpo.telefono = null;
      const { usuario: actualizado } = await perfilApi.actualizar(cuerpo);
      actualizarUsuario(actualizado);
      form.setValores(Object.fromEntries(CAMPOS.map((c) => [c, actualizado[c] ?? ""])));
      avisar(cuerpo.correo ? "Datos guardados. Usa tu nuevo correo para iniciar sesión." : "Datos guardados.");
    } catch (error) {
      form.aplicarErrorApi(error);
    } finally {
      setGuardando(false);
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
        <Campo etiqueta="Nombre" required maxLength={80} autoComplete="given-name" {...form.campo("nombre")} />
        <Campo etiqueta="Apellido" required maxLength={80} autoComplete="family-name" {...form.campo("apellido")} />
      </div>
      <div className={s.dos}>
        <Campo etiqueta="Correo electrónico" type="email" required maxLength={254} autoComplete="email" {...form.campo("correo")} />
        <Campo etiqueta="Teléfono" type="tel" maxLength={20} autoComplete="tel" ayuda="Opcional. Déjalo vacío para quitarlo" {...form.campo("telefono")} />
      </div>
      <div className={s.botones}>
        {hayCambios && (
          <Boton type="button" variante="fantasma" onClick={() => form.setValores(inicial)} disabled={guardando}>
            Descartar cambios
          </Boton>
        )}
        <Boton type="submit" cargando={guardando} disabled={!hayCambios}>
          Guardar cambios
        </Boton>
      </div>
    </form>
  );
}
