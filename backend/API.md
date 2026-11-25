# FullBikers API — Contratos REST

Contratos para el desarrollo del frontend (React).

| Estado | Significado |
|---|---|
| **Implementado** | Existe en el código, cubierto por pruebas unitarias y por pruebas de integración contra PostgreSQL 18 local real. Pendiente de verificar contra la rama `development` de Neon. |
| **Planificado** | Contrato preliminar. Aún no existe. Puede ajustarse al implementarlo; los cambios se anotarán aquí. |

> **Autenticación obligatoria.** Todo el sistema exige iniciar sesión. No existe catálogo público ni rol visitante. Los únicos endpoints públicos son `POST /api/auth/register`, `POST /api/auth/login` y los de diagnóstico (`/api/health*`).

## 1. Convenciones

| Tema | Regla |
|---|---|
| URL base | Desarrollo: `http://127.0.0.1:5000/api`. Producción: URL de Render + `/api` (en el frontend, `VITE_API_URL`). |
| Formato | JSON UTF-8 en solicitudes y respuestas (`Content-Type: application/json`). |
| Autenticación | Cabecera `Authorization: Bearer <access_token>` en **toda** ruta no pública. |
| Dinero | Cadena decimal con dos decimales: `"450000.00"` (COP). Nunca número de punto flotante. Para mostrarlo: `new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(precio))`. |
| Fechas | ISO 8601 con zona horaria (planificado para pedidos). Mostrar en `America/Bogota`. |
| Identificadores | Enteros positivos. |
| Paginación | Parámetros `pagina` (≥ 1, predeterminado 1) y `por_pagina` (1–50, predeterminado 12). La respuesta incluye `pagina`, `por_pagina` y `total_paginas`. |
| Errores | Siempre `{"error": {"codigo": "...", "mensaje": "...", "detalles": {...}?}}`. `mensaje` es apto para mostrar al usuario; el frontend decide por `codigo`. |

### Códigos de error comunes

| HTTP | `codigo` | Cuándo | Qué hace el frontend |
|---|---|---|---|
| 400 | `parametro_invalido` | Parámetro de consulta inválido; `detalles.parametro` indica cuál. | Mostrar `mensaje`. |
| 400 | `validacion` | Datos del cuerpo inválidos; `detalles.campos` = `{campo: mensaje}`. | Mostrar cada mensaje junto a su campo. |
| 400 | `campo_no_permitido` | El cuerpo trae campos no admitidos; `detalles.campos` = lista. | Error de programación: corregir el formulario. |
| 400 | `solicitud_invalida` | Cuerpo ausente, mal formado o que no es un objeto JSON. | — |
| 401 | `no_autenticado` | Falta el token, es inválido o alterado, o el usuario fue desactivado o no existe. | Borrar el token y redirigir al login. |
| 401 | `token_expirado` | El token superó sus 60 minutos. | Borrar el token y redirigir al login con "Su sesión expiró". |
| 401 | `credenciales_invalidas` | Solo en login: correo o contraseña incorrectos, o cuenta inactiva. | Mostrar `mensaje` en el formulario (no redirigir). |
| 403 | `acceso_denegado` | Usuario autenticado sin el rol necesario. | Mostrar "No tiene permisos" o volver al inicio. **No** borrar el token. |
| 404 | `recurso_no_encontrado` / específico | Ruta o recurso inexistente (o ajeno al usuario). | — |
| 405 | `metodo_no_permitido` | Método HTTP no soportado en la ruta. | — |
| 409 | `correo_ya_registrado` | Registro con un correo existente. | Mostrar en el campo correo. |
| 429 | `demasiadas_solicitudes` | 5 intentos de login fallidos en 15 min (mismo correo e IP). Cabecera `Retry-After` en segundos. | Mostrar `mensaje`; deshabilitar el botón un tiempo. |
| 500 | `error_interno` | Error inesperado. Sin detalles técnicos. | Mensaje genérico. |
| 503 | `base_de_datos_no_disponible` | PostgreSQL no configurado o no responde. | Mensaje genérico; reintentar. |

**Regla para el cliente HTTP del frontend:** ante **cualquier 401 en una ruta protegida** (todas excepto `/auth/login` y `/auth/register`) se borra el token de `sessionStorage` y se navega a `/login`. Un **403** no cierra la sesión.

## 2. Roles y permisos

Los roles se leen de la base de datos en **cada** petición protegida: un cambio de rol o una desactivación tienen efecto inmediato aunque el token siga vigente. El rol incluido en el token es solo informativo; el frontend debe usar el `rol` de `/api/auth/login` o `/api/auth/me`.

| Funcionalidad | `cliente` | `empleado` | `administrador` |
|---|:-:|:-:|:-:|
| Registro público | Solo crea clientes | — | — |
| Login, logout, `/auth/me` | ✔ | ✔ | ✔ |
| Catálogo: principal, búsqueda, filtro, detalle (RF-01–RF-05) | ✔ | ✔ (consulta de productos para pedidos e inventario) | ✔ |
| Perfil, direcciones, carrito, pedidos propios (RF-10–RF-21) | ✔ *(planificado)* | — | ✔ *(planificado)* |
| Gestión de pedidos e inventario (RF-29–RF-34) | — | ✔ *(planificado)* | ✔ *(planificado)* |
| Administración de usuarios, productos, categorías, reportes | — | — | ✔ *(planificado)* |

El administrador tiene acceso a todas las funcionalidades. Para el **menú por rol** en React basta con `usuario.rol`; la API vuelve a verificar el permiso en cada llamada (el menú solo es una ayuda visual).

## 3. Diagnóstico (públicos)

### `GET /api/health` — Implementado
Comprueba que Flask responde. No consulta PostgreSQL. Autenticación: no.

```json
200 {"estado": "OK", "servicio": "API FullBikers"}
```

### `GET /api/health/db` — Implementado
Ejecuta `SELECT 1`. Autenticación: no. No expone servidor, credenciales ni detalles del error.

```json
200 {"estado": "OK", "base_de_datos": "disponible"}
503 {"error": {"codigo": "base_de_datos_no_disponible", "mensaje": "El servicio de datos no está disponible en este momento. Intente más tarde."}}
```

## 4. Autenticación — Implementado

Tokens JWT de acceso (Flask-JWT-Extended, HS256, firmados con `JWT_SECRET_KEY`), válidos **60 minutos**, **sin refresh token**. Al expirar, la API responde `401 token_expirado` y el usuario vuelve a iniciar sesión.

### `POST /api/auth/register` — Público
Registro **exclusivo de clientes** (RF-06, RF-07). El rol siempre es `cliente` y lo asigna el backend.

```json
{"nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com",
 "contrasena": "Segura2026", "telefono": "+57 300 000 0000"}
```

| Campo | Regla |
|---|---|
| `nombre`, `apellido` | Obligatorios, 1–80 caracteres (se recortan espacios). |
| `correo` | Obligatorio, ≤ 254, formato `algo@dominio.ext`. Se guarda en minúsculas y sin espacios extremos: `Ana@Ejemplo.com` y `ana@ejemplo.com` son el mismo correo. |
| `contrasena` | Obligatoria, 8–128 caracteres, al menos una letra y un número. No se recorta. Se guarda solo su hash (scrypt, Werkzeug). |
| `telefono` | Opcional (`null`, ausente o vacío = sin teléfono). Empieza por dígito (o `+` y dígito), termina en dígito; admite dígitos, espacios, `-` y paréntesis; 7–20 caracteres. Ej.: `3001234567`, `+57 300 123 4567`. |
| Cualquier otro campo | `rol`, `activo`, `id_usuario`, etc. → `400 campo_no_permitido`; no se crea el usuario. |

```json
201 {"usuario": {"id_usuario": 7, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "telefono": "+57 300 000 0000", "rol": "cliente"}}
```
Errores:
```json
400 {"error": {"codigo": "validacion", "mensaje": "Revise los datos ingresados.",
               "detalles": {"campos": {"correo": "El correo electrónico no tiene un formato válido.",
                                       "contrasena": "La contraseña debe incluir al menos una letra y un número."}}}}
400 {"error": {"codigo": "campo_no_permitido", "mensaje": "La solicitud incluye campos no permitidos.", "detalles": {"campos": ["rol"]}}}
409 {"error": {"codigo": "correo_ya_registrado", "mensaje": "Ya existe una cuenta registrada con ese correo electrónico."}}
```
También `400 solicitud_invalida` y `503`. **No inicia sesión automáticamente:** tras el `201`, el frontend lleva al login (o llama a login con los mismos datos).

### `POST /api/auth/login` — Público
RF-08.

```json
{"correo": "ana@ejemplo.com", "contrasena": "Segura2026"}
```
```json
200 {"access_token": "<jwt>", "token_type": "Bearer", "expires_in": 3600,
     "usuario": {"id_usuario": 7, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "telefono": null, "rol": "cliente"}}
```
Errores:
```json
401 {"error": {"codigo": "credenciales_invalidas", "mensaje": "Correo electrónico o contraseña incorrectos."}}
429 {"error": {"codigo": "demasiadas_solicitudes", "mensaje": "Demasiados intentos fallidos. Intente de nuevo más tarde."}}   (+ cabecera Retry-After)
400 {"error": {"codigo": "validacion", ..., "detalles": {"campos": {"correo": "...", "contrasena": "..."}}}}
```
El `401` es idéntico para correo inexistente, contraseña incorrecta y cuenta inactiva (no revela qué correos existen). El correo se normaliza igual que en el registro.

### `POST /api/auth/logout` — Autenticado (todos los roles)
RF-09. Sin cuerpo. Responde `204` sin contenido; sin token válido, `401`.

**Cierre de sesión y su limitación:** el servidor no guarda sesiones ni revoca tokens. Cerrar sesión consiste en que el frontend **elimine el token de `sessionStorage`**. Si alguien hubiera copiado el token, este seguiría siendo válido hasta su expiración (máximo 60 minutos), salvo que el usuario sea desactivado (efecto inmediato). Es una limitación aceptada para el alcance académico del proyecto.

### `GET /api/auth/me` — Autenticado (todos los roles)
Usuario actual leído **de la base de datos** (rol y estado vigentes). Sirve para restaurar la sesión al recargar la página y construir el menú.

```json
200 {"usuario": {"id_usuario": 7, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "telefono": null, "rol": "cliente"}}
```
Errores: `401 no_autenticado` / `401 token_expirado`. Nunca devuelve contraseñas, hashes ni el estado interno.

### Guía para React

1. **Login:** `POST /auth/login` → guardar `access_token` en `sessionStorage` (no `localStorage`, no cookies) y `usuario` en el estado global (contexto).
2. **Cliente HTTP:** añadir `Authorization: Bearer <token>` a cada petición; ante `401` en rutas protegidas, borrar el token y navegar a `/login`.
3. **Recargar la página:** si hay token en `sessionStorage`, llamar a `GET /auth/me`; con `200` restaurar `usuario`, con `401` limpiar.
4. **Rutas protegidas:** sin `usuario` → `/login`. Rutas por rol: comparar `usuario.rol` (el administrador entra a todas).
5. **Logout:** `POST /auth/logout` (opcional esperar el `204`), luego borrar token y `usuario` y navegar a `/login`.
6. Nunca mostrar datos del usuario con `dangerouslySetInnerHTML`.

## 5. Catálogo — Implementado

Autenticación: **obligatoria**. Roles: `cliente`, `empleado`, `administrador`. Sin token: `401`.
Visibilidad: producto activo + categoría activa + al menos una variante activa. Stock y disponibilidad se calculan solo con variantes activas.

### `GET /api/principal`
Categorías activas y primera página de productos (más recientes primero).

| Parámetro | Tipo | Regla |
|---|---|---|
| `por_pagina` | query, entero | 1–50, predeterminado 12 |

```json
200 {
  "categorias": [{"id_categoria": 1, "nombre": "Cascos", "descripcion": "Cascos integrales...", "activo": true}],
  "productos": [ <ProductoResumen> ],
  "total_productos": 11,
  "pagina": 1, "por_pagina": 12, "total_paginas": 1
}
```
Errores: `401`, `403`, `400`, `503`, `500`.

### `GET /api/productos`
Búsqueda y filtro (RF-01, RF-02, RF-03, RF-04).

| Parámetro | Tipo | Regla |
|---|---|---|
| `categoria` | query, entero | Opcional. `id_categoria` ≥ 1. |
| `busqueda` | query, texto | Opcional. Máx. 100 caracteres; se recortan espacios. Coincidencia **parcial**, sin distinguir mayúsculas, en nombre **o** referencia. `%` y `_` se buscan literalmente (no son comodines). |
| `pagina` | query, entero | 1–10000, predeterminado 1. |
| `por_pagina` | query, entero | 1–50, predeterminado 12. |

Ejemplo: `GET /api/productos?categoria=1&busqueda=casco&pagina=1&por_pagina=12`

```json
200 {
  "productos": [
    {
      "id_producto": 1, "id_categoria": 1, "categoria": "Cascos",
      "nombre": "Casco integral Ruta X1", "referencia": "CAS-INT-001",
      "descripcion": "...", "marca": "MotoAndes",
      "precio": "450000.00", "imagen": null,
      "stock_total": 13, "disponible": true
    }
  ],
  "total_resultados": 1,
  "pagina": 1, "por_pagina": 12, "total_paginas": 1
}
```
Sin resultados: `200` con `"productos": []` y `"total_resultados": 0` (el frontend muestra "No se encontraron productos", HU02). Una página posterior a la última devuelve lista vacía.
Errores: `401`, `403`, `400 parametro_invalido`, `503`, `500`. La autenticación se comprueba antes que los parámetros.

### `GET /api/productos/{id_producto}`
Detalle con variantes activas (RF-05).

```json
200 {
  "id_producto": 2, "id_categoria": 1, "categoria": "Cascos",
  "nombre": "Casco abatible Urbano Pro", "referencia": "CAS-ABA-002",
  "descripcion": "...", "marca": "RutaSegura",
  "precio": "380000.00", "imagen": null,
  "stock_total": 5, "disponible": true,
  "variantes": [
    {"id_variante": 4, "id_producto": 2, "talla": "M", "color": "Blanco", "compatibilidad": null,
     "sku": "CAS-ABA-002-M-BLA", "stock": 3, "disponible": true}
  ]
}
```
Errores: `401`, `403`, `404 producto_no_encontrado` (inexistente, inactivo, categoría inactiva o sin variantes activas; si el id no es numérico → `404 recurso_no_encontrado`), `503`, `500`.

### Cambios respecto al PR #1

| Antes | Ahora | Motivo |
|---|---|---|
| Error: `{"error": "texto"}` | `{"error": {"codigo", "mensaje"}}` | Formato único; el frontend decide por código. |
| `precio`: número (`float`) | Cadena decimal `"450000.00"` | Sin pérdida de precisión (NUMERIC). |
| `/api/productos` devolvía todo | Paginado (`pagina`, `por_pagina`, `total_paginas`) | Límite de tamaño de respuesta. |
| `/api/principal` devolvía todos los productos; `total_productos` = cantidad devuelta | Primera página; `total_productos` = total visible | Mismo motivo. |
| `categoria=abc` se ignoraba | `400 parametro_invalido` | Validación explícita (RNF19). |
| Variantes y stock incluían variantes inactivas | Solo variantes activas | Regla de negocio (README BD §9). |
| Categoría: campo `estado` | Campo `activo` | Nombre real de la columna. |
| `/api/health` incluía `modulo_activo` | Eliminado | Sin utilidad para el diagnóstico. |
| Catálogo sin autenticación (solo en desarrollo) | Requiere `Authorization: Bearer` | Autenticación obligatoria. |

## 6. Planificados para la entrega 1 (contratos a detallar en su etapa)

| Método y ruta | RF | Roles | Estado |
|---|---|---|---|
| `GET /api/perfil` · `PUT /api/perfil` | RF-10 | cliente (propio) | Planificado |
| `GET/POST /api/direcciones` · `PUT /api/direcciones/{id}` · `PATCH /api/direcciones/{id}/principal` · `PATCH /api/direcciones/{id}/desactivar` | RF-11 | cliente (propias) | Planificado |
| `GET /api/carrito` | RF-15 | cliente | Planificado |
| `POST /api/carrito/items` `{id_variante, cantidad}` | RF-12 | cliente | Planificado |
| `PATCH /api/carrito/items/{id}` `{cantidad}` | RF-13 | cliente | Planificado |
| `DELETE /api/carrito/items/{id}` (borrado lógico) | RF-14 | cliente | Planificado |
| `POST /api/pedidos` `{id_direccion, observaciones}` | RF-16–RF-19 | cliente | Planificado |
| `GET /api/pedidos` · `GET /api/pedidos/{id}` | RF-20, RF-21 | cliente (propios) | Planificado |

Los recursos de cliente se filtran siempre por el usuario del token; un recurso ajeno responde `404` (no `403`) para no revelar su existencia (`exigir_propietario` en `middleware/auth.py`).
