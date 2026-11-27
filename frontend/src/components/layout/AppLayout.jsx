import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, Home, LayoutGrid, LogOut, ShoppingBag, UserRound } from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { useCarrito } from "../../features/carrito/useCarrito";
import { useCajonCarrito } from "../../features/carrito/CajonCarrito";
import { NOMBRE_ROL, puedeComprar } from "../../utils/roles";
import Logo from "./Logo";
import s from "./AppLayout.module.css";

const NAVEGACION = [
  { to: "/", texto: "Inicio", icono: Home, exacto: true },
  { to: "/productos", texto: "Catálogo", icono: LayoutGrid },
];

export default function AppLayout() {
  const { usuario } = useAuth();
  const { pathname } = useLocation();
  const comprador = puedeComprar(usuario);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);

  return (
    <div className={s.app}>
      <a href="#contenido" className={s.saltar}>
        Ir al contenido
      </a>
      <header className={s.header}>
        <div className={`contenedor ${s.barra}`}>
          <Link to="/" className={s.marca} aria-label="FullBikers, ir al inicio">
            <Logo />
          </Link>

          <nav className={s.nav} aria-label="Principal">
            <Navegacion />
          </nav>

          <div className={s.acciones}>
            {comprador && <BotonCarrito />}
            <MenuUsuario />
          </div>
        </div>
      </header>

      <motion.main
        id="contenido"
        key={pathname}
        className={s.main}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        <Outlet />
      </motion.main>

      <footer className={s.footer}>
        <div className="contenedor">
          <p>
            <strong>FullBikers</strong>, equipo para motociclistas desde Tuluá, Valle del Cauca. Envíos a toda Colombia.
          </p>
        </div>
      </footer>

      <nav className={s.navMovil} aria-label="Principal (móvil)">
        <Navegacion movil comprador={comprador} />
      </nav>
    </div>
  );
}

function Navegacion({ movil = false, comprador = false }) {
  const { abrir } = useCajonCarrito();
  const grupo = movil ? "nav-movil" : "nav";
  return (
    <>
      {NAVEGACION.map(({ to, texto, icono: Icono, exacto }) => (
        <NavLink key={to} to={to} end={exacto} className={({ isActive }) => `${s.enlace} ${isActive ? s.activo : ""}`}>
          {({ isActive }) => (
            <>
              {isActive && <motion.span layoutId={`${grupo}-indicador`} className={s.indicador} transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              <Icono size={movil ? 20 : 17} aria-hidden className={s.iconoNav} />
              <span>{texto}</span>
            </>
          )}
        </NavLink>
      ))}
      {movil && comprador && (
        <button type="button" className={s.enlace} onClick={abrir}>
          <ShoppingBag size={20} aria-hidden className={s.iconoNav} />
          <span>Carrito</span>
          <ContadorMovil />
        </button>
      )}
      {movil && (
        <NavLink to="/cuenta" className={({ isActive }) => `${s.enlace} ${isActive ? s.activo : ""}`}>
          {({ isActive }) => (
            <>
              {isActive && <motion.span layoutId={`${grupo}-indicador`} className={s.indicador} transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              <UserRound size={20} aria-hidden className={s.iconoNav} />
              <span>Cuenta</span>
            </>
          )}
        </NavLink>
      )}
    </>
  );
}

function ContadorMovil() {
  const { data: carrito } = useCarrito();
  const unidades = carrito?.cantidad_unidades ?? 0;
  if (!unidades) return null;
  return (
    <motion.span key={unidades} className={`${s.contador} ${s.contadorMovil} numero`} initial={{ scale: 0.4 }} animate={{ scale: [1.35, 1] }}>
      {unidades > 99 ? "99+" : unidades}
    </motion.span>
  );
}

function BotonCarrito() {
  const { data: carrito } = useCarrito();
  const { abrir } = useCajonCarrito();
  const unidades = carrito?.cantidad_unidades ?? 0;
  return (
    <button type="button" className={s.carrito} onClick={abrir} aria-label={`Abrir carrito, ${unidades} unidades`}>
      <ShoppingBag size={20} aria-hidden />
      <AnimatePresence>
        {unidades > 0 && (
          <motion.span
            key={unidades}
            className={`${s.contador} numero`}
            initial={{ scale: 0.4, opacity: 0 }}
            animate={{ scale: [1.35, 1], opacity: 1 }}
            exit={{ scale: 0.4, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          >
            {unidades > 99 ? "99+" : unidades}
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}

function MenuUsuario() {
  const { usuario, cerrarSesion } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [saliendo, setSaliendo] = useState(false);
  const contenedor = useRef(null);
  const { pathname } = useLocation();

  useEffect(() => setAbierto(false), [pathname]);

  useEffect(() => {
    if (!abierto) return;
    const fuera = (e) => !contenedor.current?.contains(e.target) && setAbierto(false);
    const escape = (e) => e.key === "Escape" && setAbierto(false);
    document.addEventListener("pointerdown", fuera);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", fuera);
      document.removeEventListener("keydown", escape);
    };
  }, [abierto]);

  const iniciales = `${usuario.nombre?.[0] ?? ""}${usuario.apellido?.[0] ?? ""}`.toUpperCase();

  const salir = async () => {
    setSaliendo(true);
    await cerrarSesion();
  };

  return (
    <div className={s.usuario} ref={contenedor}>
      <button type="button" className={s.avatarBoton} onClick={() => setAbierto((a) => !a)} aria-expanded={abierto} aria-haspopup="menu">
        <span className={s.avatar} aria-hidden>
          {iniciales}
        </span>
        <span className={s.nombreUsuario}>{usuario.nombre}</span>
        <motion.span animate={{ rotate: abierto ? 180 : 0 }} className={s.flecha}>
          <ChevronDown size={16} aria-hidden />
        </motion.span>
      </button>
      <AnimatePresence>
        {abierto && (
          <motion.div
            role="menu"
            className={s.menu}
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 480, damping: 34 }}
          >
            <div className={s.menuCabecera}>
              <strong>
                {usuario.nombre} {usuario.apellido}
              </strong>
              <span>{usuario.correo}</span>
              <span className={s.rol}>{NOMBRE_ROL[usuario.rol] ?? usuario.rol}</span>
            </div>
            <Link role="menuitem" to="/cuenta" className={s.menuItem}>
              <UserRound size={17} aria-hidden /> Mi cuenta
            </Link>
            <button role="menuitem" type="button" className={s.menuItem} onClick={salir} disabled={saliendo}>
              <LogOut size={17} aria-hidden /> {saliendo ? "Cerrando sesión…" : "Cerrar sesión"}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
