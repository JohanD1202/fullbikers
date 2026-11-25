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
| 404 | `direccion_no_encontrada` / `item_no_encontrado` / `variante_no_encontrada` | Dirección o artículo de carrito inexistente, inactivo o **ajeno**; variante inexistente. | Recargar la lista. |
| 409 | `correo_ya_registrado` | Registro o cambio de perfil con un correo de otra cuenta. | Mostrar en el campo correo. |
| 409 | `stock_insuficiente` | La cantidad pedida (o la resultante en el carrito) supera el stock; `detalles.stock_disponible` (y `cantidad_en_carrito` al agregar). | Mostrar y ajustar el selector de cantidad. |
| 409 | `producto_no_disponible` | Producto, categoría o variante inactivos. | Sugerir retirar el artículo. |
| 409 | `carrito_no_modificable` | El carrito ya fue convertido en pedido o abandonado. | Recargar `GET /carrito`. |
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
| Actualizar perfil propio (RF-10) | ✔ | — (solo `/auth/me`) | ✔ (el suyo) |
| Direcciones propias (RF-11) y carrito propio (RF-12–RF-15) | ✔ | — | ✔ (los suyos) |
| Pedidos propios (RF-16–RF-21) | ✔ *(planificado)* | — | ✔ *(planificado)* |
| Gestión de pedidos e inventario (RF-29–RF-34) | — | ✔ *(planificado)* | ✔ *(planificado)* |
| Administración de usuarios, productos, categorías, reportes | — | — | ✔ *(planificado)* |

El administrador tiene acceso a todas las funcionalidades; en perfil, direcciones y carrito opera sobre **sus propios** datos (la gestión de otros usuarios pertenece al módulo de administración). Un empleado que llame a perfil, direcciones o carrito recibe `403`. Para el **menú por rol** en React basta con `usuario.rol`; la API vuelve a verificar el permiso en cada llamada (el menú solo es una ayuda visual).

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

## 6. Perfil (RF-10) — Implementado

### Consultar: `GET /api/auth/me`
Se reutiliza el endpoint de §4: devuelve los datos personales vigentes.

### `PATCH /api/perfil` — Roles: `cliente`, `administrador` (cada uno el suyo)
Actualización **parcial**: se envían solo los campos que cambian (al menos uno). El usuario se toma del token.

```json
{"nombre": "Ana María", "apellido": "Pérez", "correo": "ana.maria@ejemplo.com", "telefono": "300 123 4567"}
```

| Campo | Regla |
|---|---|
| `nombre`, `apellido` | 1–80 caracteres; no pueden quedar vacíos. |
| `correo` | Mismas reglas que el registro; se normaliza a minúsculas. Si pertenece a otra cuenta → `409 correo_ya_registrado`. Tras cambiarlo, el usuario inicia sesión con el nuevo correo (el token actual sigue siendo válido). |
| `telefono` | Mismas reglas que el registro; `null` o `""` lo elimina. |
| Otros (`rol`, `activo`, `id_usuario`, `contrasena`, …) | `400 campo_no_permitido`; no se cambia nada. |

```json
200 {"usuario": {"id_usuario": 7, "nombre": "Ana María", "apellido": "Pérez", "correo": "ana.maria@ejemplo.com", "telefono": "300 123 4567", "rol": "cliente"}}
```
Errores: `400 validacion` (con `detalles.campos`; cuerpo `{}` → campo `_`), `400 campo_no_permitido`, `400 solicitud_invalida`, `401`, `403` (empleado), `409 correo_ya_registrado`.
Fuera de alcance: cambio y recuperación de contraseña, verificación por correo.

## 7. Direcciones (RF-11) — Implementado

Roles: `cliente`, `administrador` (cada uno **sus** direcciones). El propietario siempre es el usuario del token; una dirección ajena, inexistente o eliminada responde `404 direccion_no_encontrada`.

**Objeto `Direccion`:**
```json
{"id_direccion": 12, "departamento": "Valle del Cauca", "municipio": "Tuluá",
 "direccion": "Calle 26 # 30-15", "complemento": "Apto 301, barrio Centro",
 "codigo_postal": "763021", "principal": true}
```

| Campo | Regla |
|---|---|
| `departamento` | Obligatorio, 1–60 caracteres. |
| `municipio` | Obligatorio, 1–80. |
| `direccion` | Obligatorio, 1–150. |
| `complemento` | Opcional, ≤ 100 (`null`/`""` = sin complemento). |
| `codigo_postal` | Opcional, 4–10 dígitos. |
| `principal` | Opcional, `true`/`false`. Como máximo **una** principal: marcar una desmarca la anterior. La **primera** dirección del usuario queda principal automáticamente. |
| Otros (`id_usuario`, `activo`, `id_direccion`, …) | `400 campo_no_permitido`. |

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /api/direcciones` | — | `200 {"direcciones": [Direccion, ...]}` solo activas; la principal primero. Lista vacía si no hay. |
| `POST /api/direcciones` | Obligatorios + opcionales | `201 {"direccion": Direccion}` |
| `GET /api/direcciones/{id}` | — | `200 {"direccion": Direccion}` |
| `PATCH /api/direcciones/{id}` | Uno o más campos (parcial) | `200 {"direccion": Direccion}`. Para **seleccionar** la principal: `{"principal": true}` |
| `DELETE /api/direcciones/{id}` | — | `204`. **Eliminación lógica** (`activo = false`; deja de ser principal). No se elige otra principal automáticamente. |

Errores: `400 validacion`, `400 campo_no_permitido`, `401`, `403` (empleado), `404 direccion_no_encontrada`.
Los pedidos guardan una **copia** de la dirección de entrega: editar o eliminar una dirección no altera pedidos anteriores.

## 8. Carrito de compras (RF-12 a RF-15) — Implementado

Roles: `cliente`, `administrador` (cada uno **su** carrito). Cada usuario tiene como máximo un carrito **abierto**; se crea automáticamente al agregar el primer artículo. **Todas** las operaciones devuelven el carrito completo y recalculado:

```json
200 {"carrito": {
  "id_carrito": 31,
  "estado": "abierto",
  "items": [
    {"id_detalle_carrito": 88, "id_producto": 1, "id_variante": 2,
     "nombre": "Casco integral Ruta X1", "referencia": "CAS-INT-001", "marca": "MotoAndes",
     "categoria": "Cascos", "imagen": null,
     "sku": "CAS-INT-001-M-NEG", "talla": "M", "color": "Negro mate", "compatibilidad": null,
     "cantidad": 2, "precio_unitario": "450000.00", "subtotal": "900000.00",
     "stock_disponible": 8, "disponible": true, "motivo_no_disponible": null}
  ],
  "cantidad_items": 1, "cantidad_unidades": 2,
  "total": "900000.00",
  "vacio": false, "todos_disponibles": true
}}
```

| Campo | Significado |
|---|---|
| `id_carrito` | `null` si el usuario aún no tiene carrito abierto (carrito vacío; **no** es un error). |
| `precio_unitario` | Precio **vigente** del producto (el carrito no guarda precios; si cambia el precio, el carrito lo refleja). |
| `subtotal` / `total` | Calculados en el servidor con `Decimal`: `subtotal = precio_unitario × cantidad`; `total` = suma de los subtotales de **todas** las líneas mostradas (incluidas las no disponibles). Cadenas con dos decimales. |
| `stock_disponible` | Unidades actuales de la variante (`0` si el producto, la categoría o la variante están inactivos). |
| `disponible` / `motivo_no_disponible` | `false` y un motivo si el artículo no se puede comprar ahora: `producto_inactivo`, `categoria_inactiva`, `variante_inactiva`, `sin_stock`, `stock_insuficiente` (cantidad > stock). Estos artículos **no se ocultan ni se eliminan**: el cliente los ve y decide retirarlos o bajar la cantidad. |
| `todos_disponibles` | `true` si todas las líneas están disponibles (sugerencia para habilitar "Confirmar pedido"). |
| `vacio` | `true` si no hay líneas activas. |

| Método y ruta | Cuerpo | Notas |
|---|---|---|
| `GET /api/carrito` | — | Consulta con subtotales y total. Carrito vacío con `id_carrito: null` si no existe. |
| `POST /api/carrito/items` | `{"id_producto": 1, "id_variante": 2, "cantidad": 1}` | RF-12. `id_variante` es **obligatorio** (para productos sin talla/color/compatibilidad, usar su variante base: la única de `variantes` en el detalle). Si la variante ya está en el carrito, **suma** la cantidad. Si se había retirado, se reactiva su línea. `cantidad`: entero ≥ 1 (no cadenas ni decimales). Cualquier otro campo (p. ej. `precio`) → `400 campo_no_permitido`. Responde `200`. |
| `PATCH /api/carrito/items/{id_detalle_carrito}` | `{"cantidad": 3}` | RF-13. **Fija** la nueva cantidad (no suma). |
| `DELETE /api/carrito/items/{id_detalle_carrito}` | — | RF-14. Retira la línea (borrado lógico). Responde `200` con el carrito (puede quedar vacío). Se permite aunque el producto esté inactivo o sin stock. |

Reglas al **agregar** y al **modificar**: producto, categoría y variante activos (si no, `409 producto_no_disponible`); la cantidad resultante ≤ stock actual (si no, `409 stock_insuficiente` con `detalles`). La variante debe pertenecer al producto (si no, `400 validacion` en `id_variante`); variante inexistente → `404 variante_no_encontrada`.

Errores: `400 validacion` / `campo_no_permitido` / `solicitud_invalida`, `401`, `403` (empleado), `404 item_no_encontrado` (línea inexistente, ya retirada o de otro usuario), `404 variante_no_encontrada`, `409 stock_insuficiente`, `409 producto_no_disponible`, `409 carrito_no_modificable` (convertido o abandonado), `503`.

**Importante:** el carrito **no reserva ni descuenta stock**. La disponibilidad mostrada puede cambiar antes de confirmar el pedido; el módulo de pedidos vuelve a validarla.

### Guía para React (perfil, direcciones y carrito)

1. **Perfil:** cargar con `GET /auth/me`; guardar con `PATCH /perfil` enviando solo lo editado; mostrar `detalles.campos` junto a cada input. Actualizar el `usuario` del contexto con la respuesta.
2. **Direcciones:** listar con `GET /direcciones`; alta/edición con `POST` / `PATCH`; botón "Usar como principal" = `PATCH {"principal": true}`; eliminar = `DELETE` (204) y recargar la lista.
3. **Carrito:** el detalle del producto ofrece un selector de variante (`variantes` de `GET /productos/{id}`; deshabilitar las que tienen `disponible: false`) y llama a `POST /carrito/items`. Guardar en el estado global el `carrito` devuelto por **cualquier** operación (no hace falta un `GET` posterior). Ícono del encabezado: `cantidad_unidades`.
4. Mostrar importes con `Intl.NumberFormat` (§1). Nunca calcular el total en el navegador ni enviar precios.
5. Para cada línea con `disponible: false`, mostrar un aviso según `motivo_no_disponible` y ofrecer "Retirar" (y "Ajustar a `stock_disponible`" si es `stock_insuficiente`).
6. Ante `409 carrito_no_modificable`, volver a pedir `GET /carrito`.

## 9. Contrato con el módulo de pedidos (RF-16 a RF-19)

Para quien implemente `POST /api/pedidos`. El carrito **no** crea pedidos, no descuenta stock, no genera movimientos ni cambia el estado del carrito; todo eso corresponde al servicio de pedidos, en **una sola transacción**.

| Tema | Contrato |
|---|---|
| Estados de `carrito.estado` | `abierto` (el único modificable; máx. uno activo por usuario, índice `ux_carrito_abierto_por_usuario`), `convertido` (ya generó pedido), `abandonado`. El módulo del carrito solo lee y crea carritos `abierto`. |
| Carrito abierto | `CarritoDAO.obtener_abierto(conn, id_usuario, bloquear=True)` → `dict` (`id_carrito`, `id_usuario`, `estado`, `fecha_creacion`, `activo`) o `None`. Con `bloquear=True` bloquea la fila (`FOR NO KEY UPDATE`) hasta el fin de la transacción: ninguna operación del carrito puede modificarlo mientras se registra el pedido. |
| Líneas activas | `CarritoDAO.listar_items(conn, id_carrito)` → lista de `ItemCarrito` (`models/carrito.py`) con `id_detalle_carrito`, `id_producto`, `id_variante`, `cantidad` (int > 0), `precio` (Decimal, **vigente**), `stock`, `producto_activo`, `categoria_activa`, `variante_activa`, `subtotal` (Decimal), `disponible` y `motivo_no_disponible`. Incluye las líneas no disponibles (no se filtran). |
| Carrito vacío | `obtener_abierto` devuelve `None`, o `listar_items` devuelve `[]` → rechazar el pedido. |
| Producto y variante | `detalle_carrito` guarda `(id_producto, id_variante)` con FK compuesta a `variante_producto (id_variante, id_producto)`: la variante siempre pertenece al producto. Todo producto vendible tiene al menos una variante (la base si no tiene características). `ProductoDAO.obtener_variante_para_venta(conn, id_variante)` devuelve `id_producto`, `stock`, `precio` y los tres indicadores de actividad. |
| Precios | El carrito no guarda precios: usa `producto.precio` (`NUMERIC(14,2)`, Decimal en Python). El pedido debe **copiar** `precio_unitario` y calcular `subtotal` en `detalle_pedido`, y `pedido.subtotal`/`total`, con `models.dinero.a_decimal`. `Carrito(items=...).total` ya suma los subtotales con Decimal. |
| Validaciones que hace el carrito | Al agregar o modificar: activos y cantidad ≤ stock **en ese momento**. No reserva. |
| Validaciones que **debe repetir** pedidos | Dentro de su transacción: (1) carrito abierto del usuario, bloqueado; (2) al menos una línea; (3) para cada línea, producto, categoría y variante activos; (4) **descontar stock con UPDATE condicional** `UPDATE variante_producto SET stock = stock - %s WHERE id_variante = %s AND activo AND stock >= %s RETURNING stock` (0 filas → abortar con `409 stock_insuficiente`); (5) dirección activa del usuario (`DireccionDAO.obtener_activa(conn, id_direccion, id_usuario)`) y copia de sus campos al pedido; (6) un `movimiento_inventario` de salida por línea; (7) cerrar el carrito con transición condicional `UPDATE carrito SET estado = 'convertido' WHERE id_carrito = %s AND id_usuario = %s AND estado = 'abierto' AND activo` (0 filas → abortar). Ver `database/README.md` §8.3. |
| Transacción | Abrir `with database.transaccion() as conn:` en el servicio de pedidos y pasar **la misma** `conn` a `CarritoDAO`, `ProductoDAO`, `DireccionDAO` y a los DAO de pedidos e inventario. Los DAO nunca hacen `commit`/`rollback`: cualquier excepción revierte todo. |
| Después del pedido | Las líneas del carrito convertido se conservan (`activo = true`) como historial. El siguiente `POST /api/carrito/items` del cliente crea automáticamente un carrito abierto nuevo. |
| Permisos | `fullbikers_app` ya tiene lo necesario (`SELECT/INSERT/UPDATE` en carrito, detalle_carrito, pedido, variante_producto; `SELECT/INSERT` en detalle_pedido y movimiento_inventario). |

## 10. Planificados para la entrega 1 (contratos a detallar en su etapa)

| Método y ruta | RF | Roles | Estado |
|---|---|---|---|
| `POST /api/pedidos` `{id_direccion, observaciones}` | RF-16–RF-19 | cliente | Planificado (ver §9) |
| `GET /api/pedidos` · `GET /api/pedidos/{id}` | RF-20, RF-21 | cliente (propios) | Planificado |

Los recursos de cliente se filtran siempre por el usuario del token; un recurso ajeno responde `404` (no `403`) para no revelar su existencia.
