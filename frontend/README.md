# FullBikers — Frontend (React)

Vista de la aplicación FullBikers. Consume la API Flask del directorio `backend/` con los contratos de [`backend/API.md`](../backend/API.md). No se conecta nunca a PostgreSQL.

## 1. Estado

| Funcionalidad | RF | Endpoints | Estado |
|---|---|---|---|
| Login, registro (con inicio de sesión automático), logout, restaurar sesión al recargar | RF-06 a RF-09 | `/auth/*` | Implementado y probado (pruebas automatizadas) |
| Rutas protegidas, menú por rol, 401 → login ("Su sesión expiró"), 403 sin cerrar sesión, 429 con cuenta regresiva | — | — | Implementado y probado |
| Página principal, búsqueda en vivo, filtro por categoría, paginación (estado en la URL) | RF-01 a RF-04 | `/principal`, `/productos` | Implementado y probado |
| Detalle de producto con selector de variantes y existencias | RF-05 | `/productos/{id}` | Implementado y probado |
| Carrito: cajón lateral, página, cantidades, retirar, avisos de no disponibilidad, "Ajustar a N" | RF-12 a RF-15 | `/carrito*` | Implementado y probado |
| Perfil (PATCH solo con los campos cambiados) | RF-10 | `/auth/me`, `/perfil` | Implementado y probado |
| Direcciones: alta, edición, principal, eliminación con confirmación | RF-11 | `/direcciones*` | Implementado y probado |
| Registrar pedido (dirección → revisión → confirmar) y detalle con estado | RF-16 a RF-19 | `/pedidos` | Implementado y probado |
| Historial de pedidos | RF-20, RF-21 | `GET /api/pedidos` | **Bloqueado: el endpoint aún no existe en el backend** |
| Gestión de pedidos e inventario (empleado), administración | RF-29 a RF-34 y siguientes | — | **Bloqueado: sin endpoints** |

**Integración real pendiente:** todo lo anterior se verificó con pruebas automatizadas que simulan la API con las respuestas documentadas en `API.md`, y visualmente en el navegador. Falta probarlo contra el backend en ejecución (ver §6).

El empleado ve el catálogo en "vista de consulta" (existencias por variante) y su cuenta en solo lectura. La API le responde 403 en carrito, direcciones y perfil.

## 2. Tecnologías

| Paquete | Uso | Motivo |
|---|---|---|
| React 19 + Vite 8 | Base | Decisión del proyecto (README raíz) |
| react-router 8 | Rutas y guardas por rol | Navegación de la SPA |
| @tanstack/react-query 5 | Datos del servidor | Caché, carga, errores y reintentos. El carrito devuelto por cada operación se guarda sin hacer otro GET |
| motion | Animaciones | Interfaz fluida: indicadores que se deslizan, cajón del carrito, cuadrícula que se reacomoda. Respeta "reducir movimiento" |
| lucide-react | Iconos | Consistentes y accesibles |
| Vitest, Testing Library, MSW, jsdom | Pruebas | MSW simula la API **solo en las pruebas** |

Estilos con CSS Modules y variables (`src/styles/tokens.css`), sin framework de CSS. Tipografía Archivo (Google Fonts) con su eje de anchura.

## 3. Estructura

```
src/
├── api/            client.js (fetch + token + errores), endpoints.js (un objeto por recurso)
├── auth/           AuthContext (sesión), Guards (RequiereSesion, RequiereRol, SoloInvitados)
├── components/
│   ├── layout/     AppLayout (encabezado, navegación inferior en móvil), Logo
│   └── ui/         Boton, Campo, Modal, Avisos, SelectorCantidad, ImagenProducto, LineaVial, ...
├── features/       catalogo/, carrito/, direcciones/ (hooks de datos y componentes del dominio)
├── hooks/          useFormulario (errores por campo del navegador y de la API)
├── pages/          una página por ruta
├── utils/          format (COP, fechas America/Bogota), validacion (mismas reglas del backend), roles
└── test/           pruebas (unitarias y de flujos completos)
```

Rutas: `/login`, `/registro`, `/`, `/productos`, `/productos/:id`, `/cuenta`, y para cliente/administrador `/carrito`, `/pedido`, `/pedidos/:id`.

## 4. Ejecución

Requisitos: Node 20 o superior.

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local   # VITE_API_URL=http://127.0.0.1:5000/api
npm run dev                          # http://localhost:5173
```

El backend debe estar en marcha (`flask --app app run --debug`) con `CORS_ORIGINS=http://localhost:5173`. Abrir el frontend como `http://localhost:5173`, no como `127.0.0.1:5173`: es el origen que admite CORS.

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo |
| `npm test` | Pruebas (31) |
| `npm run build` | Compilación de producción en `dist/` |

## 5. Despliegue en Netlify (no realizado)

Base directory `frontend`, build `npm run build`, publish `frontend/dist`, variable `VITE_API_URL` = URL de Render + `/api`. `public/_redirects` envía todas las rutas a `index.html`. En Render, `CORS_ORIGINS` debe incluir la URL de Netlify.

## 6. Pendientes

1. Probar contra el backend real (rama `development` de Neon) los flujos de §1.
2. Cuando exista `GET /api/pedidos`: página "Mis pedidos" y enlace en el menú.
3. Módulos de empleado y administrador cuando el backend publique sus endpoints.
4. Imágenes: `producto.imagen` es `null` en la semilla. Se muestra un marcador con la marca y la referencia; con una URL real se muestra la foto.
