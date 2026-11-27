import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, Info } from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { destinoSeguro } from "../../auth/Guards";
import useFormulario from "../../hooks/useFormulario";
import Campo from "../../components/ui/Campo";
import Boton from "../../components/ui/Boton";
import * as v from "../../utils/validacion";
import AuthLayout from "./AuthLayout";
import s from "./Auth.module.css";

const validar = (val) => ({
  correo: v.correo(val.correo),
  contrasena: val.contrasena ? null : "La contraseña es obligatoria.",
});

export default function LoginPage() {
  const { iniciarSesion, avisoLogin, setAvisoLogin } = useAuth();
  const navegar = useNavigate();
  const { state } = useLocation();
  const form = useFormulario({ correo: state?.correo ?? "", contrasena: "" }, validar);
  const [enviando, setEnviando] = useState(false);
  const [espera, setEspera] = useState(0);

  // 429: cuenta regresiva según Retry-After antes de permitir otro intento.
  useEffect(() => {
    if (espera <= 0) return;
    const t = window.setTimeout(() => setEspera((n) => n - 1), 1000);
    return () => window.clearTimeout(t);
  }, [espera]);

  const enviar = async (e) => {
    e.preventDefault();
    form.setErrorGeneral(null);
    if (!form.validarTodo()) return;
    setEnviando(true);
    try {
      await iniciarSesion({ correo: form.valores.correo.trim(), contrasena: form.valores.contrasena });
      navegar(destinoSeguro(state?.desde), { replace: true });
    } catch (error) {
      if (error.codigo === "demasiadas_solicitudes") setEspera(error.retryAfter ?? 60);
      form.aplicarErrorApi(error);
      setEnviando(false);
    }
  };

  const minutos = Math.ceil(espera / 60);

  return (
    <AuthLayout titulo="Inicia sesión" subtitulo="Ingresa para ver el catálogo, tu carrito y tus pedidos.">
      <AnimatePresence>
        {avisoLogin && !form.errorGeneral && (
          <motion.div className={`${s.alerta} ${s.info}`} role="status" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            <Info size={18} aria-hidden /> <span>{avisoLogin}</span>
          </motion.div>
        )}
        {form.errorGeneral && (
          <motion.div
            key={form.errorGeneral}
            className={s.alerta}
            role="alert"
            initial={{ opacity: 0, x: 0 }}
            animate={{ opacity: 1, x: [0, -8, 8, -4, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <AlertTriangle size={18} aria-hidden />
            <span>
              {form.errorGeneral}
              {espera > 0 && ` Podrá intentarlo de nuevo en ${espera < 60 ? `${espera} s` : `${minutos} min`}.`}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      <form className={s.campos} onSubmit={enviar} noValidate>
        <Campo etiqueta="Correo electrónico" type="email" autoComplete="email" required {...form.campo("correo")} onFocus={() => setAvisoLogin(null)} />
        <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" required {...form.campo("contrasena")} />
        <Boton type="submit" tamano="lg" className={s.enviar} cargando={enviando} disabled={espera > 0}>
          {espera > 0 ? "Espere para intentarlo de nuevo" : "Iniciar sesión"}
        </Boton>
      </form>

      <p className={s.alterno}>
        ¿Aún no tienes cuenta? <Link to="/registro">Crea una cuenta</Link>
      </p>
    </AuthLayout>
  );
}
