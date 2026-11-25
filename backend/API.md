# FullBikers API — Contratos REST

Contratos actuales y preliminares para el desarrollo paralelo del frontend.

| Estado | Significado |
|---|---|
| **Implementado (dev)** | Existe en el código, cubierto por pruebas unitarias con *mocks*. Pendiente de verificación real contra la rama `development` de Neon. **No** se considera terminado: le falta la autenticación obligatoria. |
| **Planificado** | Contrato preliminar. Aún no existe. Puede ajustarse al implementarlo; los cambios se anotarán aquí. |

> **Autenticación obligatoria.** Todo el sistema exige iniciar sesión. Los únicos endpoints públicos son `POST /api/auth/register`, `POST /api/auth/login` y los de diagnóstico (`/api/health*`). Los endpoints del catálogo **requerirán** un token válido antes de considerarse terminados; mientras tanto solo se usan en desarrollo local y la aplicación **no los registra en producción**.

## 1. Convenciones

| Tema | Regla |
|---|---|
| URL base | Desarrollo: `http://127.0.0.1:5000/api`. Producción: URL de Render + `/api` (se configura en el frontend con `VITE_API_URL`). |
| Formato | JSON UTF-8 en solicitudes y respuestas. |
| Autenticación (planificada) | Cabecera `Authorization: Bearer <access_token>`. |
| Dinero | Cadena decimal con dos decimales: `"450000.00"` (COP). Nunca número de punto flotante. Para mostrarlo: `new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(precio))`. |
| Fechas | ISO 8601 con zona horaria (planificado para pedidos). Mostrar en `America/Bogota`. |
| Identificadores | Enteros positivos. |
| Paginación | Parámetros `pagina` (≥ 1, predeterminado 1) y `por_pagina` (1–50, predeterminado 12). La respuesta incluye `pagina`, `por_pagina` y `total_paginas`. |
| Errores | Siempre `{"error": {"codigo": "...", "mensaje": "...", "detalles": {...}?}}`. `mensaje` es apto para mostrar al usuario; el frontend decide por `codigo`. |

### Códigos de error comunes

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 400 | `parametro_invalido` | Parámetro de consulta inválido; `detalles.parametro` indica cuál. |
| 400 | `solicitud_invalida` | Cuerpo mal formado. |
| 401 | `no_autenticado` | *(Planificado)* Falta el token, es inválido o expiró. El frontend redirige al login. |
| 403 | `acceso_denegado` | *(Planificado)* El rol no tiene permiso. |
| 404 | `recurso_no_encontrado` / específico | Ruta o recurso inexistente (o ajeno al usuario). |
| 405 | `metodo_no_permitido` | Método HTTP no soportado en la ruta. |
| 409 | específico | *(Planificado)* Conflicto de negocio (p. ej., `correo_ya_registrado`). |
| 429 | `demasiadas_solicitudes` | *(Planificado)* Demasiados intentos de inicio de sesión. |
| 500 | `error_interno` | Error inesperado. Sin detalles técnicos. |
| 503 | `base_de_datos_no_disponible` | PostgreSQL no configurado o no responde. |

## 2. Diagnóstico (públicos)

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

## 3. Catálogo — Implementado (dev), requerirá autenticación

Autenticación requerida (al terminar): **sí**. Roles: `cliente`, `empleado`, `administrador`.
Visibilidad: producto activo + categoría activa + al menos una variante activa. Stock y disponibilidad se calculan solo con variantes activas.
Errores adicionales al terminar: `401`.

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
Errores: `400`, `503`, `500`.

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
Errores: `400 parametro_invalido`, `503`, `500`.

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
Errores: `404 producto_no_encontrado` (inexistente, inactivo, categoría inactiva o sin variantes activas; también si el id no es numérico → `404 recurso_no_encontrado`), `503`, `500`.

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

## 4. Autenticación — Planificado

Tokens JWT (Flask-JWT-Extended) firmados con `JWT_SECRET_KEY`, válidos **60 minutos**, sin *refresh token*. Al expirar, la API responde `401 no_autenticado` y el frontend vuelve al login. Detalles de diseño: `backend/README.md` §8.

### `POST /api/auth/register` — Público
Registro **exclusivo de clientes** (RF-06, RF-07). El rol siempre es `cliente`.

```json
{"nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com",
 "contrasena": "Segura2026", "telefono": "+57 300 000 0000"}
```
Reglas: `nombre`, `apellido` (1–80), `correo` (normalizado a minúsculas, formato válido, ≤ 254), `contrasena` (8–128, al menos una letra y un número), `telefono` opcional. Cualquier campo no listado (p. ej. `rol`, `activo`, `id_usuario`) → `400 campo_no_permitido`.

```json
201 {"usuario": {"id_usuario": 7, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "telefono": "+57 300 000 0000", "rol": "cliente"}}
```
Errores: `400 validacion` (con `detalles.campos`), `400 campo_no_permitido`, `409 correo_ya_registrado`, `503`.
No inicia sesión automáticamente (el frontend redirige al login), salvo que el equipo decida lo contrario.

### `POST /api/auth/login` — Público
RF-08. `{"correo": "...", "contrasena": "..."}`

```json
200 {"access_token": "<jwt>", "token_type": "Bearer", "expires_in": 3600,
     "usuario": {"id_usuario": 7, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "rol": "cliente"}}
```
Errores: `401 credenciales_invalidas` (mismo mensaje para correo inexistente, contraseña incorrecta o cuenta inactiva), `429 demasiadas_solicitudes`, `400 validacion`, `503`.

### `POST /api/auth/logout` — Autenticado (todos los roles)
RF-09. Sin cuerpo. `204` sin contenido. El frontend borra el token. Ver la estrategia de revocación en `backend/README.md` §8.

### `GET /api/auth/me` — Autenticado (todos los roles)
Usuario actual leído **de la base de datos** (rol y estado vigentes), para restaurar la sesión al recargar y construir el menú.

```json
200 {"usuario": {"id_usuario": 7, "nombre": "Ana", "apellido": "Pérez", "correo": "ana@ejemplo.com", "telefono": null, "rol": "cliente"}}
```
Errores: `401 no_autenticado` (token ausente, inválido, expirado, o usuario desactivado).

## 5. Planificados para la entrega 1 (contratos a detallar en su etapa)

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

Los recursos de cliente se filtran siempre por el usuario del token; un recurso ajeno responde `404` (no `403`) para no revelar su existencia.
