import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { AlertTriangle } from "lucide-react";

import { authApi } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import useFormulario from "../../hooks/useFormulario";
import Campo from "../../components/ui/Campo";
import Boton from "../../components/ui/Boton";
import { useAvisos } from "../../components/ui/Avisos";
import * as v from "../../utils/validacion";
import AuthLayout from "./AuthLayout";
import s from "./Auth.module.css";

const validar = (val) => ({
  ...v.validarPersona(val),
  contrasena: v.contrasena(val.contrasena),
  confirmacion: val.confirmacion !== val.contrasena ? "Las contraseñas no coinciden." : null,
});

/** Seguridad de la contraseña según las reglas del backend (8+, letra y número). */
function Requisitos({ clave }) {
  const reglas = [
    { ok: clave.length >= 8 && clave.length <= 128, texto: "8 caracteres o más" },
    { ok: /\p{L}/u.test(clave), texto: "Una letra" },
    { ok: /\p{Nd}/u.test(clave), texto: "Un número" },
  ];
  return (
    <ul style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", margin: "-0.4rem 0 0.6rem", padding: 0, listStyle: "none" }} aria-label="Requisitos de la contraseña">
      {reglas.map((r) => (
        <li
          key={r.texto}
          style={{
            padding: "2px 10px",
            borderRadius: 999,
            fontSize: "var(--t-xs)",
            fontWeight: 600,
            transition: "background-color .25s, color .25s",
            background: r.ok ? "var(--exito-suave)" : "var(--neblina-2)",
            color: r.ok ? "var(--exito)" : "var(--musgo)",
          }}
        >
          {r.ok ? "✓ " : ""}
          {r.texto}
        </li>
      ))}
    </ul>
  );
}

export default function RegistroPage() {
  const { iniciarSesion } = useAuth();
  const { avisar } = useAvisos();
  const navegar = useNavigate();
  const [enviando, setEnviando] = useState(false);
  const form = useFormulario({ nombre: "", apellido: "", correo: "", telefono: "", contrasena: "", confirmacion: "" }, validar);

  const enviar = async (e) => {
    e.preventDefault();
    form.setErrorGeneral(null);
    if (!form.validarTodo()) return;
    setEnviando(true);
    const { nombre, apellido, correo, telefono, contrasena } = form.valores;
    try {
      await authApi.registrar({
        nombre: nombre.trim(),
        apellido: apellido.trim(),
        correo: correo.trim(),
        telefono: telefono.trim() || null,
        contrasena,
      });
    } catch (error) {
      form.aplicarErrorApi(error);
      setEnviando(false);
      return;
    }
    // El registro no inicia sesión: se hace login con los mismos datos (API.md §4).
    try {
      await iniciarSesion({ correo: correo.trim(), contrasena });
      avisar(`Bienvenido a FullBikers, ${nombre.trim()}.`);
      navegar("/", { replace: true });
    } catch {
      navegar("/login", { replace: true, state: { correo: correo.trim() } });
    }
  };

  return (
    <AuthLayout titulo="Crea tu cuenta" subtitulo="Compra en línea y recibe tu equipo en cualquier lugar de Colombia.">
      {form.errorGeneral && (
        <div className={s.alerta} role="alert">
          <AlertTriangle size={18} aria-hidden /> <span>{form.errorGeneral}</span>
        </div>
      )}
      <form className={s.campos} onSubmit={enviar} noValidate>
        <div className={s.dosColumnas}>
          <Campo etiqueta="Nombre" autoComplete="given-name" required maxLength={80} {...form.campo("nombre")} />
          <Campo etiqueta="Apellido" autoComplete="family-name" required maxLength={80} {...form.campo("apellido")} />
        </div>
        <Campo etiqueta="Correo electrónico" type="email" autoComplete="email" required maxLength={254} {...form.campo("correo")} />
        <Campo etiqueta="Teléfono" type="tel" autoComplete="tel" maxLength={20} ayuda="Opcional. Ej.: 300 123 4567" {...form.campo("telefono")} />
        <Campo etiqueta="Contraseña" type="password" autoComplete="new-password" required maxLength={128} {...form.campo("contrasena")} />
        <Requisitos clave={form.valores.contrasena} />
        <Campo etiqueta="Confirmar contraseña" type="password" autoComplete="new-password" required maxLength={128} {...form.campo("confirmacion")} />
        <Boton type="submit" tamano="lg" className={s.enviar} cargando={enviando}>
          Crear cuenta
        </Boton>
      </form>
      <p className={s.alterno}>
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </AuthLayout>
  );
}
