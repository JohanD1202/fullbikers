# FullBikers — Base de datos

Esquema relacional de **FullBikers**, tienda virtual B2C de accesorios y artículos para motociclistas (Tuluá, Valle del Cauca). Proyecto académico de *Desarrollo de Software I* — Tecnología en Desarrollo de Software, Universidad del Valle.

| Elemento | Valor |
|---|---|
| Motor | PostgreSQL 18 (objetivo: 18.7 en Neon). Mínimo técnico: 15 (`UNIQUE NULLS NOT DISTINCT`) |
| Base de datos | `fullbikers` (ya existe; el script no la crea) |
| Rama Neon | `production` |
| Esquema | `public` |
| Versión del esquema | 1.0.0 (inicial) |
| Moneda | COP, `NUMERIC(14,2)` |
| Zona horaria de negocio | `America/Bogota` (las fechas se guardan como `TIMESTAMPTZ`) |
| Backend previsto | Python + Flask (MVC + DAO) con Psycopg 3. React **nunca** se conecta a PostgreSQL. |

## Contenido

1. [Archivos](#1-archivos)
2. [Ejecución manual en Neon](#2-ejecución-manual-en-neon)
3. [Tablas](#3-tablas)
4. [Relaciones y cardinalidades](#4-relaciones-y-cardinalidades)
5. [Convenciones](#5-convenciones)
6. [Reglas de negocio: qué garantiza PostgreSQL y qué Flask](#6-reglas-de-negocio-qué-garantiza-postgresql-y-qué-flask)
7. [Estados y transiciones](#7-estados-y-transiciones)
8. [Estrategia de inventario](#8-estrategia-de-inventario)
9. [Estrategia de borrado lógico](#9-estrategia-de-borrado-lógico)
10. [Decisiones técnicas](#10-decisiones-técnicas)
11. [Diferencias respecto al MER, al diagrama de clases y al documento](#11-diferencias-respecto-al-mer-al-diagrama-de-clases-y-al-documento)
12. [Índices](#12-índices)
13. [Seguridad](#13-seguridad)
14. [Responsabilidades del backend](#14-responsabilidades-del-backend)
15. [Consultas de referencia para la capa DAO](#15-consultas-de-referencia-para-la-capa-dao)
16. [Futuras migraciones](#16-futuras-migraciones)
17. [Limitaciones y decisiones pendientes](#17-limitaciones-y-decisiones-pendientes)
18. [Pruebas realizadas](#18-pruebas-realizadas)

---

## 1. Archivos

| Archivo | Propósito |
|---|---|
| `schema.sql` | Crea las 10 tablas, restricciones, índices y comentarios en **una sola transacción**. Sin `DROP`, `TRUNCATE`, `CREATE DATABASE` ni `IF NOT EXISTS`. Sin datos. |
| `verification.sql` | Consultas **de solo lectura** (transacción `READ ONLY` + `ROLLBACK`) para verificar estructura e integridad. |
| `README.md` | Este documento. |

## 2. Ejecución manual en Neon

> El script está pensado para una base **vacía**. Si alguna tabla ya existe, falla con `relation "..." already exists` y, por estar en una transacción, **no crea nada**.

1. Entrar a la consola de Neon → proyecto FullBikers → **SQL Editor**.
2. Seleccionar la rama **`production`**, la base **`fullbikers`** y el rol **`fullbikers_owner`**.
3. (Opcional) Confirmar que la base está vacía:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public';          -- esperado: 0 filas
   ```
4. Pegar el contenido completo de `schema.sql` y ejecutarlo. El resultado final debe ser `COMMIT`.
5. Pegar y ejecutar `verification.sql`. Resultados esperados:
   - 10 tablas existentes, todas con `cumple_minimo = true` (≥ 5 atributos).
   - 10 claves primarias, 13 claves foráneas (todas `RESTRICT`), 8 restricciones UNIQUE, 4 índices únicos parciales/por expresión, 44 restricciones CHECK, 33 índices en total.
   - `activo` presente en las 10 tablas con `cumple = true`.
   - 0 triggers y 0 privilegios concedidos a `PUBLIC`.
   - Consultas de integridad (14 a 20): 0 filas en una base recién creada.
6. Si se prefiere `psql` en lugar del editor web, usar una variable de entorno (nunca escribir la cadena de conexión en archivos del repositorio):
   ```bash
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql
   psql "$DATABASE_URL" -f database/verification.sql
   ```

**Zona horaria.** Las fechas se almacenan como instantes absolutos (`TIMESTAMPTZ`). Para mostrarlas en hora de Colombia, el backend puede ejecutar `SET TIME ZONE 'America/Bogota'` al abrir cada conexión o convertir con `fecha AT TIME ZONE 'America/Bogota'`. Opcionalmente, el equipo puede fijarlo para toda la base con `ALTER DATABASE fullbikers SET timezone TO 'America/Bogota';` (no está incluido en `schema.sql` porque modifica la base, no el esquema).

## 3. Tablas

Diez tablas, en orden de creación (respeta dependencias de claves foráneas). Todas tienen PK `INTEGER GENERATED ALWAYS AS IDENTITY` y `activo BOOLEAN NOT NULL DEFAULT TRUE`.

### 3.1 `usuario`
Personas que acceden al sistema.

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_usuario | INTEGER IDENTITY | No | — | PK |
| nombre | VARCHAR(80) | No | — | No vacío |
| apellido | VARCHAR(80) | No | — | No vacío |
| correo | VARCHAR(254) | No | — | UNIQUE; debe estar en minúsculas y sin espacios extremos; formato básico `x@y.z`. 254 = longitud máxima práctica de un correo |
| contrasena_hash | VARCHAR(255) | No | — | Hash generado por Flask; mínimo 20 caracteres (barrera contra texto plano evidente) |
| telefono | VARCHAR(20) | Sí | — | Texto; dígitos, `+`, espacios, guiones y paréntesis |
| rol | VARCHAR(20) | No | `'cliente'` | `cliente` \| `empleado` \| `administrador` |
| activo | BOOLEAN | No | `TRUE` | Reemplaza a `estado` del MER |
| fecha_registro | TIMESTAMPTZ | No | `CURRENT_TIMESTAMP` | |

### 3.2 `direccion`
Direcciones de entrega de cada usuario.

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_direccion | INTEGER IDENTITY | No | — | PK |
| id_usuario | INTEGER | No | — | FK → usuario |
| departamento | VARCHAR(60) | No | — | |
| municipio | VARCHAR(80) | No | — | |
| direccion | VARCHAR(150) | No | — | |
| complemento | VARCHAR(100) | Sí | — | Apto, barrio, referencias |
| codigo_postal | VARCHAR(10) | Sí | — | Solo dígitos, 4 a 10 (en Colombia son 6) |
| principal | BOOLEAN | No | `FALSE` | Máximo una principal activa por usuario |
| activo | BOOLEAN | No | `TRUE` | Una dirección inactiva no puede ser principal |

Clave alterna `UNIQUE (id_direccion, id_usuario)`: la usa la FK compuesta de `pedido`.

### 3.3 `categoria`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_categoria | INTEGER IDENTITY | No | — | PK |
| nombre | VARCHAR(60) | No | — | Único sin distinguir mayúsculas (índice `uq_categoria_nombre_ci`); sin espacios extremos |
| descripcion | TEXT | Sí | — | |
| activo | BOOLEAN | No | `TRUE` | Reemplaza a `estado` |
| fecha_creacion | TIMESTAMPTZ | No | `CURRENT_TIMESTAMP` | **Nueva**: completa el mínimo de 5 atributos |

### 3.4 `producto`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_producto | INTEGER IDENTITY | No | — | PK |
| id_categoria | INTEGER | No | — | FK → categoria |
| nombre | VARCHAR(150) | No | — | |
| referencia | VARCHAR(50) | No | — | UNIQUE; almacenada en MAYÚSCULAS sin espacios extremos |
| descripcion | TEXT | Sí | — | |
| marca | VARCHAR(80) | Sí | — | |
| precio | NUMERIC(14,2) | No | — | ≥ 0, COP. Precio vigente |
| imagen | VARCHAR(500) | Sí | — | URL o ruta de almacenamiento (no binario) |
| activo | BOOLEAN | No | `TRUE` | Reemplaza a `estado` |

### 3.5 `variante_producto`
Única fuente del inventario.

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_variante | INTEGER IDENTITY | No | — | PK |
| id_producto | INTEGER | No | — | FK → producto |
| talla | VARCHAR(20) | Sí | — | NULL si no aplica (nunca cadena vacía) |
| color | VARCHAR(40) | Sí | — | NULL si no aplica |
| compatibilidad | VARCHAR(150) | Sí | — | NULL si no aplica |
| sku | VARCHAR(60) | No | — | UNIQUE; MAYÚSCULAS, `A-Z 0-9 . _ / -`, sin espacios |
| stock | INTEGER | No | `0` | ≥ 0 |
| stock_minimo | INTEGER | No | `5` | **Nueva**: umbral de stock bajo (RF-34), ≥ 0 |
| activo | BOOLEAN | No | `TRUE` | |

- `UNIQUE (id_variante, id_producto)`: clave alterna para las FK compuestas de los detalles.
- `UNIQUE NULLS NOT DISTINCT (id_producto, talla, color, compatibilidad)`: no hay combinaciones repetidas y **un producto no puede tener dos variantes base**.

### 3.6 `carrito`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_carrito | INTEGER IDENTITY | No | — | PK |
| id_usuario | INTEGER | No | — | FK → usuario |
| fecha_creacion | TIMESTAMPTZ | No | `CURRENT_TIMESTAMP` | |
| estado | VARCHAR(20) | No | `'abierto'` | `abierto` \| `convertido` \| `abandonado` |
| activo | BOOLEAN | No | `TRUE` | |

Índice único parcial: como máximo **un carrito abierto y activo** por usuario.

### 3.7 `detalle_carrito`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_detalle_carrito | INTEGER IDENTITY | No | — | PK |
| id_carrito | INTEGER | No | — | FK → carrito |
| id_producto | INTEGER | No | — | Parte de la FK compuesta |
| id_variante | INTEGER | No | — | FK compuesta `(id_variante, id_producto)` → variante_producto. **Ahora obligatoria** |
| cantidad | INTEGER | No | — | > 0 |
| activo | BOOLEAN | No | `TRUE` | Retirar del carrito = `activo = false` |

Índice único parcial: una sola línea **activa** por `(id_carrito, id_variante)`.

### 3.8 `pedido`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_pedido | INTEGER IDENTITY | No | — | PK; identificador único del pedido (RF-18) |
| id_usuario | INTEGER | No | — | Parte de la FK compuesta |
| id_direccion | INTEGER | No | — | FK compuesta `(id_direccion, id_usuario)` → direccion |
| fecha | TIMESTAMPTZ | No | `CURRENT_TIMESTAMP` | |
| estado | VARCHAR(20) | No | `'pendiente'` | Ver §7 |
| subtotal | NUMERIC(14,2) | No | — | ≥ 0; suma de líneas (calcula el backend) |
| total | NUMERIC(14,2) | No | — | ≥ subtotal |
| observaciones | TEXT | Sí | — | Máx. 1000 caracteres |
| departamento_entrega | VARCHAR(60) | No | — | **Nueva**: copia histórica |
| municipio_entrega | VARCHAR(80) | No | — | **Nueva**: copia histórica |
| direccion_entrega | VARCHAR(150) | No | — | **Nueva**: copia histórica |
| complemento_entrega | VARCHAR(100) | Sí | — | **Nueva**: copia histórica |
| codigo_postal_entrega | VARCHAR(10) | Sí | — | **Nueva**: copia histórica |
| fecha_actualizacion | TIMESTAMPTZ | No | `CURRENT_TIMESTAMP` | **Nueva**: último cambio de estado (HU12); ≥ fecha |
| id_usuario_actualizacion | INTEGER | Sí | — | **Nueva**: FK → usuario; responsable del último cambio (RNF16). Obligatoria si `estado <> 'pendiente'` |
| activo | BOOLEAN | No | `TRUE` | No equivale a cancelar |

### 3.9 `detalle_pedido`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_detalle | INTEGER IDENTITY | No | — | PK |
| id_pedido | INTEGER | No | — | FK → pedido |
| id_producto | INTEGER | No | — | Parte de la FK compuesta |
| id_variante | INTEGER | No | — | FK compuesta → variante_producto. **Ahora obligatoria** |
| cantidad | INTEGER | No | — | > 0 |
| precio_unitario | NUMERIC(14,2) | No | — | ≥ 0; precio al momento del pedido |
| subtotal | NUMERIC(14,2) | (generada) | — | `GENERATED ALWAYS AS (cantidad * precio_unitario) STORED` |
| activo | BOOLEAN | No | `TRUE` | |

`UNIQUE (id_pedido, id_variante)`: una línea por variante en cada pedido (también es la clave que referencia `movimiento_inventario`).

### 3.10 `movimiento_inventario`

| Columna | Tipo | Nulo | Predeterminado | Notas |
|---|---|---|---|---|
| id_movimiento | INTEGER IDENTITY | No | — | PK |
| id_variante | INTEGER | No | — | FK → variante_producto |
| id_usuario | INTEGER | No | — | FK → usuario (responsable) |
| id_pedido | INTEGER | Sí | — | **Nueva**: FK compuesta opcional `(id_pedido, id_variante)` → detalle_pedido |
| tipo | VARCHAR(10) | No | — | `entrada` \| `salida` \| `ajuste` |
| cantidad | INTEGER | No | — | entrada/salida: > 0; ajuste: ≠ 0 con signo |
| stock_anterior | INTEGER | No | — | **Nueva**: ≥ 0 |
| stock_nuevo | INTEGER | No | — | **Nueva**: ≥ 0 y coherente con tipo y cantidad |
| fecha | TIMESTAMPTZ | No | `CURRENT_TIMESTAMP` | |
| motivo | VARCHAR(255) | No | — | No vacío |
| activo | BOOLEAN | No | `TRUE` | No afecta el stock (ver §9) |

## 4. Relaciones y cardinalidades

| Relación (MER) | Tablas | Cardinalidad | Implementación |
|---|---|---|---|
| registra | usuario → direccion | 1 : 0..N | `fk_direccion_usuario` |
| posee | usuario → carrito | 1 : 0..N (máx. 1 abierto) | `fk_carrito_usuario` + `ux_carrito_abierto_por_usuario` |
| realiza | usuario → pedido | 1 : 0..N | `fk_pedido_direccion_usuario` (compuesta) |
| es_destino_de | direccion → pedido | 1 : 0..N | `fk_pedido_direccion_usuario` (compuesta) |
| registra (inventario) | usuario → movimiento_inventario | 1 : 0..N | `fk_movimiento_inventario_usuario` |
| — (último cambio de estado) | usuario → pedido | 1 : 0..N | `fk_pedido_usuario_actualizacion` (nueva) |
| agrupa | categoria → producto | 1 : 0..N | `fk_producto_categoria` |
| tiene | producto → variante_producto | 1 : **1..N** | `fk_variante_producto_producto` (el "al menos una" lo garantiza el backend) |
| contiene | carrito → detalle_carrito | 1 : 0..N | `fk_detalle_carrito_carrito` |
| se_agrega_en / especifica | producto/variante → detalle_carrito | 1 : 0..N | `fk_detalle_carrito_variante_producto` (compuesta) |
| incluye | pedido → detalle_pedido | 1 : 1..N | `fk_detalle_pedido_pedido` (el "al menos una" lo garantiza el backend) |
| se_vende_en / especifica | producto/variante → detalle_pedido | 1 : 0..N | `fk_detalle_pedido_variante_producto` (compuesta) |
| afecta_stock | variante_producto → movimiento_inventario | 1 : 0..N | `fk_movimiento_inventario_variante` |
| — (origen del movimiento) | detalle_pedido → movimiento_inventario | 1 : 0..2 (una salida y como máximo una entrada) | `fk_movimiento_inventario_detalle_pedido` + `uq_movimiento_inventario_pedido_variante_tipo` (nuevas) |

Todas las FK son `ON DELETE RESTRICT ON UPDATE RESTRICT`. Las FK compuestas usan `MATCH SIMPLE` (predeterminado): si `id_pedido` es `NULL` en un movimiento manual, esa FK no se evalúa.

## 5. Convenciones

- Identificadores en español, minúsculas, `snake_case`, sin tildes ni espacios; tablas en singular.
- PK: `id_<tabla>` con `INTEGER GENERATED ALWAYS AS IDENTITY` (la aplicación no puede asignar ids manualmente).
- Dinero: `NUMERIC(14,2)` (hasta 999.999.999.999,99 COP). Nunca `FLOAT`/`REAL`/`DOUBLE PRECISION`.
- Fechas de eventos: `TIMESTAMPTZ` con `DEFAULT CURRENT_TIMESTAMP`.
- Teléfono y código postal: texto.
- Nombres de restricciones e índices:

| Prefijo | Significado |
|---|---|
| `pk_` | clave primaria |
| `fk_` | clave foránea |
| `uq_` | restricción UNIQUE (o índice único por expresión) |
| `ux_` | índice único parcial |
| `ck_` | restricción CHECK |
| `ix_` | índice no único |

- Longitudes `VARCHAR`: correo 254 (límite práctico RFC), hash 255 (scrypt/argon2/bcrypt caben con holgura), imagen 500 (URL con parámetros), nombres de persona 80, nombre de producto 150, referencia 50, SKU 60, textos de dirección 60–150, estados 20, tipo de movimiento 10. Textos libres largos: `TEXT`.

## 6. Reglas de negocio: qué garantiza PostgreSQL y qué Flask

| Regla | PostgreSQL (declarativo) | Flask (backend) |
|---|---|---|
| Correo único sin distinguir mayúsculas | `UNIQUE` + `CHECK` de normalización | Normalizar con `correo.strip().lower()` antes de insertar **y** de consultar; traducir el error `23505` a "correo ya registrado" (RF-07) |
| Contraseñas nunca en texto plano | `CHECK` de longitud mínima (barrera parcial) | Generar el hash (p. ej. `werkzeug.security.generate_password_hash`) y verificarlo al iniciar sesión |
| Rol válido; `cliente` por defecto | `CHECK` + `DEFAULT` | Autorizar cada endpoint según el rol; el registro público **nunca** acepta un `rol` enviado por el cliente |
| Una dirección principal activa | Índice único parcial + `CHECK (activo OR NOT principal)` | Cambiar la principal en dos sentencias dentro de una transacción: primero desmarcar la actual, luego marcar la nueva |
| Pedido con dirección del mismo usuario | FK compuesta | Tomar `id_usuario` de la sesión, nunca del cuerpo de la petición |
| Variante pertenece al producto | FK compuestas en ambos detalles | — |
| Producto con al menos una variante | No expresable sin triggers | Crear producto + variante(s) en la misma transacción; el catálogo solo muestra productos con variantes activas |
| Un carrito abierto por usuario | Índice único parcial | Obtener o crear el carrito abierto |
| Línea de carrito sin duplicados | Índice único parcial `WHERE activo` | Si la variante ya está, sumar la cantidad (o `INSERT ... ON CONFLICT (id_carrito, id_variante) WHERE activo DO UPDATE`) |
| Cantidades > 0, precios ≥ 0, stock ≥ 0 | `CHECK` | Validar antes de guardar (mensajes claros, RNF-18/19) |
| Precio histórico | `precio_unitario` independiente de `producto.precio` | Copiar `producto.precio` al crear el pedido |
| Subtotal de línea | Columna generada | No enviar `subtotal` en el `INSERT` |
| Subtotal y total del pedido | `CHECK (subtotal >= 0)`, `CHECK (total >= subtotal)` | Calcular `subtotal = Σ líneas`; hoy `total = subtotal` |
| Pedido con al menos una línea | No expresable sin triggers | Rechazar carritos vacíos; consulta 15 de `verification.sql` detecta inconsistencias |
| Transiciones de estado válidas | `CHECK` del conjunto de estados; responsable obligatorio fuera de `pendiente` | Aplicar la tabla de §7 con `UPDATE ... WHERE estado = <esperado>` |
| Coherencia de movimientos | `CHECK` tipo/cantidad/stock, `UNIQUE` por pedido-variante-tipo, FK a la línea del pedido | Seguir los protocolos de §8 |
| Catálogo público: productos activos de categorías activas | — | Filtro en las consultas (ver §15) |

## 7. Estados y transiciones

### Pedido

Estado inicial: `pendiente`.

```
pendiente ──► confirmado ──► en_preparacion ──► enviado ──► entregado
    │              │                │
    └──────────────┴────────────────┴──► cancelado
```

| Desde | Hacia | Quién | Efecto en inventario |
|---|---|---|---|
| (nuevo) | pendiente | cliente | Descuenta stock (salidas con `id_pedido`) |
| pendiente | confirmado | empleado, administrador | Ninguno (no vuelve a descontar) |
| confirmado | en_preparacion | empleado, administrador | Ninguno |
| en_preparacion | enviado | empleado, administrador | Ninguno |
| enviado | entregado | empleado, administrador | Ninguno |
| pendiente | cancelado | cliente dueño, empleado, administrador | Devuelve stock (entradas con `id_pedido`) |
| confirmado, en_preparacion | cancelado | empleado, administrador | Devuelve stock |
| enviado, entregado, cancelado | cualquiera | — | **No permitido** (estados finales o ya despachados) |

Cada cambio de estado actualiza `fecha_actualizacion = CURRENT_TIMESTAMP` e `id_usuario_actualizacion = <usuario autenticado>`. La base exige el responsable en todo estado distinto de `pendiente`.

### Carrito

Estado inicial: `abierto`. `abierto → convertido` (al generar el pedido, en la misma transacción) y `abierto → abandonado` (el cliente lo vacía/descarta o un proceso de limpieza). `convertido` y `abandonado` son finales.

## 8. Estrategia de inventario

### 8.1 Principios

- **Una sola fuente:** el stock vive únicamente en `variante_producto.stock`. Un producto sin talla/color/compatibilidad tiene una **variante base** (las tres columnas en `NULL`).
- **Una sola vía de modificación:** solo el DAO de inventario cambia `stock`, y siempre en la misma transacción en que inserta el `movimiento_inventario` correspondiente. **No hay triggers** que también lo modifiquen: no existe riesgo de doble descuento por mecanismos redundantes.
- **Bitácora inmutable:** los movimientos no se editan ni se eliminan. Un error se corrige con un nuevo `ajuste`.
- **Semántica de `cantidad`:** `entrada` y `salida` usan unidades positivas; `ajuste` usa la **diferencia con signo** aplicada (+3 suma, −2 resta). Nunca 0.
- **Coherencia:** `stock_nuevo = stock_anterior + cantidad` (entrada/ajuste) o `stock_anterior − cantidad` (salida), ambos ≥ 0.

### 8.2 Movimiento manual (RF-29/RF-30, empleado o administrador)

```sql
-- Una transacción. :delta = +cantidad (entrada), -cantidad (salida) o la diferencia (ajuste).
WITH upd AS (
    UPDATE variante_producto
       SET stock = stock + :delta
     WHERE id_variante = :id_variante
       AND stock + :delta >= 0
    RETURNING id_variante, stock - :delta AS stock_anterior, stock AS stock_nuevo
)
INSERT INTO movimiento_inventario
       (id_variante, id_usuario, tipo, cantidad, stock_anterior, stock_nuevo, motivo)
SELECT id_variante, :id_usuario, :tipo, :cantidad, stock_anterior, stock_nuevo, :motivo
FROM upd
RETURNING id_movimiento;
-- Si no devuelve fila: variante inexistente o stock insuficiente → ROLLBACK y mensaje al usuario.
```

El `UPDATE` toma un bloqueo de fila: si dos empleados operan la misma variante a la vez, el segundo espera a que el primero confirme y recalcula sobre el valor ya actualizado. Por eso `stock_anterior` sale del propio `UPDATE ... RETURNING` y no de un `SELECT` previo (que podría estar desactualizado).

### 8.3 Registro de pedido (RF-16 a RF-19) — una transacción

1. **Cerrar el carrito** con transición condicional (evita doble envío por doble clic o dos pestañas):
   `UPDATE carrito SET estado = 'convertido' WHERE id_carrito = :c AND id_usuario = :u AND estado = 'abierto' AND activo RETURNING id_carrito;` → 0 filas = abortar.
2. Leer las líneas activas del carrito con el precio vigente; verificar que producto, categoría y variante estén activos. Rechazar si no hay líneas.
3. Insertar `pedido` (estado `pendiente`) copiando la dirección:
   `INSERT INTO pedido (..., departamento_entrega, ...) SELECT ..., d.departamento, ... FROM direccion d WHERE d.id_direccion = :dir AND d.id_usuario = :u AND d.activo;`
4. Insertar `detalle_pedido` con `precio_unitario = producto.precio`.
5. Para cada línea, **ordenadas por `id_variante`** (orden fijo para evitar interbloqueos entre pedidos concurrentes): `UPDATE variante_producto SET stock = stock - :cant WHERE id_variante = :v AND activo AND stock >= :cant RETURNING ...`. Si alguna no devuelve fila → `ROLLBACK` completo y aviso de "stock insuficiente" (RF-16).
6. Insertar un movimiento `salida` por línea con `id_pedido`, `id_usuario = cliente`, `stock_anterior`/`stock_nuevo` del paso 5.
7. Calcular y guardar `subtotal`/`total`. `COMMIT`.

### 8.4 Cancelación — una transacción

1. **Transición condicional** (la clave contra cancelaciones repetidas y carreras):
   ```sql
   UPDATE pedido
      SET estado = 'cancelado',
          fecha_actualizacion = CURRENT_TIMESTAMP,
          id_usuario_actualizacion = :id_usuario
    WHERE id_pedido = :id_pedido
      AND estado IN ('pendiente', 'confirmado', 'en_preparacion')   -- cliente: solo 'pendiente'
   RETURNING id_pedido;
   ```
   Si devuelve 0 filas, el pedido ya estaba cancelado, enviado o entregado → `ROLLBACK`, sin tocar el stock. Si dos usuarios cancelan a la vez, el segundo queda bloqueado por la fila del pedido y, al reevaluar, ya no cumple el `WHERE`.
2. Por cada línea (ordenada por `id_variante`): `UPDATE variante_producto SET stock = stock + :cant ... RETURNING` e insertar un movimiento `entrada` con `id_pedido`.
3. `COMMIT`.

**Barrera adicional en la base:** `uq_movimiento_inventario_pedido_variante_tipo` permite **una sola salida y una sola entrada** por pedido y variante. Aunque el backend tuviera un error y repitiera la devolución, el segundo `INSERT` falla (`23505`) y la transacción completa —incluida la actualización de stock— se revierte.

### 8.5 Confirmación y demás transiciones

`UPDATE pedido SET estado = :nuevo, fecha_actualizacion = CURRENT_TIMESTAMP, id_usuario_actualizacion = :u WHERE id_pedido = :p AND estado = :estado_esperado RETURNING id_pedido;` — no toca el inventario. La "verificación de disponibilidad" del empleado (HU21) es una consulta informativa: el stock ya quedó reservado al registrar el pedido.

### 8.6 Concurrencia — resumen

| Riesgo | Mitigación |
|---|---|
| Dos clientes compran la última unidad | `UPDATE ... WHERE stock >= :cant` + bloqueo de fila; `CHECK (stock >= 0)` como última barrera |
| Doble envío del mismo carrito | Transición condicional `abierto → convertido` |
| Cancelación repetida / devolución duplicada | Transición condicional del pedido + `UNIQUE (id_pedido, id_variante, tipo)` |
| Empleados ajustando la misma variante | `stock_anterior` tomado del `UPDATE ... RETURNING` |
| Interbloqueos entre pedidos con varias líneas | Actualizar variantes siempre en orden ascendente de `id_variante` |
| Stock modificado dos veces por mecanismos redundantes | Sin triggers; solo el DAO de inventario actualiza `stock` |

Nivel de aislamiento recomendado: el predeterminado de PostgreSQL (`READ COMMITTED`) es suficiente con estos patrones. En Psycopg 3, usar `with conn.transaction():` para cada operación.

## 9. Estrategia de borrado lógico

- Ninguna operación de la aplicación debe ejecutar `DELETE`. "Eliminar" = `UPDATE <tabla> SET activo = false`. Las FK `RESTRICT` impiden borrados físicos que dejen huérfanos.
- Desactivar **no propaga** a las tablas hijas (no hay cascadas ni triggers). Las consultas filtran por `activo` donde corresponde:

| Se desactiva | Efecto esperado (implementar en Flask) |
|---|---|
| categoria | Sus productos dejan de mostrarse en el catálogo público (filtro `c.activo`). Los productos conservan su propio `activo`; al reactivar la categoría reaparecen. Los pedidos no cambian. |
| producto | Sale del catálogo; no se puede agregar al carrito ni comprar. Las líneas de carrito abiertas que lo contengan deben marcarse inactivas o advertirse al cliente al confirmar. Pedidos y movimientos se conservan. |
| variante_producto | No se puede seleccionar ni vender. Su stock se conserva (para reactivar o ajustar). Una variante inactiva sigue ocupando su combinación talla/color/compatibilidad y su SKU: para "volver a crearla", reactivarla. |
| usuario | No puede iniciar sesión (verificar `activo` en el login). Sus pedidos, direcciones y movimientos se conservan. Es recomendable marcar su carrito abierto como `abandonado`. |
| direccion | No se ofrece para nuevos pedidos; antes de desactivarla, quitar `principal`. Los pedidos anteriores conservan su copia. |
| carrito / detalle_carrito | Retirar un artículo = `activo = false` en la línea (RF-14). |
| pedido | Solo ocultamiento administrativo. **Cancelar no es desactivar**: se usa `estado = 'cancelado'`. |
| detalle_pedido | En operación normal nunca se desactiva. |
| movimiento_inventario | **No modifica el stock ni anula el movimiento.** La trazabilidad, el kárdex y las consultas de integridad usan **todos** los movimientos, activos o no. Para corregir, registrar un `ajuste`. |

## 10. Decisiones técnicas

1. **Variante base obligatoria (D1).** Centraliza el inventario en `variante_producto`, unifica la trazabilidad y coincide con la cardinalidad 1..N del MER. `id_variante` es `NOT NULL` en los detalles.
2. **`id_producto` conservado en los detalles** (redundancia controlada). Facilita reportes por producto y respeta el MER; la FK compuesta impide que contradiga a la variante.
3. **FK compuestas en lugar de triggers** para "la dirección es del mismo usuario", "la variante es del producto" y "el movimiento corresponde a una línea del pedido".
4. **Descuento de stock al registrar el pedido (D2)**, devolución al cancelar; la confirmación del empleado no toca el inventario.
5. **Copia histórica de la dirección en `pedido` (D4, O3).** Desnormalización intencional: el pedido debe reflejar dónde se entregó aunque el cliente edite o desactive su dirección. `id_direccion` se conserva como referencia. Esta copia no viola el propósito de 3FN porque representa un hecho distinto (la dirección *en el momento del pedido*), no un dato derivable del estado actual.
6. **Solo el último cambio de estado (D5)**: `fecha_actualizacion` e `id_usuario_actualizacion`. Sin tabla de historial.
7. **`stock_anterior` / `stock_nuevo` e `id_pedido` en movimientos (D6, O1, O2)** con `CHECK` de coherencia.
8. **`stock_minimo` por variante (D7)**, predeterminado 5.
9. **`detalle_pedido.subtotal` como columna generada `STORED`** (en PostgreSQL 18 el valor predeterminado sería `VIRTUAL`; se declara `STORED` explícitamente para que el valor quede persistido y sea indexable).
10. **Normalización de textos clave** mediante `CHECK` (no se transforman datos en la base): correo en minúsculas, referencia y SKU en mayúsculas, nombre de categoría sin espacios extremos y único sin distinguir mayúsculas.
11. **Sin extensiones** (`citext`, `pg_trgm`, etc.) ni funciones/triggers.
12. **Script atómico y no idempotente**: `BEGIN … COMMIT` sin `IF NOT EXISTS`; un esquema previo provoca un fallo seguro.

## 11. Diferencias respecto al MER, al diagrama de clases y al documento

Lista para actualizar los documentos del proyecto.

### 11.1 Respecto al MER (§7.12)

| Tabla | Cambio |
|---|---|
| Todas | + `activo BOOLEAN NOT NULL DEFAULT TRUE`. Tipos concretados: `INTEGER IDENTITY`, `VARCHAR(n)`, `NUMERIC(14,2)`, `TIMESTAMPTZ` (antes `timestamp`). |
| usuario | `estado` → `activo`. `rol` con valores restringidos y predeterminado `cliente`. |
| direccion | + clave alterna `UNIQUE (id_direccion, id_usuario)`. |
| categoria | `estado` → `activo`. + `fecha_creacion`. Unicidad del nombre sin distinguir mayúsculas. |
| producto | `estado` → `activo`. |
| variante_producto | + `stock_minimo`. + `UNIQUE (id_variante, id_producto)` y `UNIQUE NULLS NOT DISTINCT (id_producto, talla, color, compatibilidad)`. |
| carrito | Valores de `estado` definidos (`abierto`, `convertido`, `abandonado`). |
| detalle_carrito | `id_variante` pasa de **opcional a obligatoria**; FK compuesta `(id_variante, id_producto)` en lugar de dos FK independientes. |
| pedido | + `departamento_entrega`, `municipio_entrega`, `direccion_entrega`, `complemento_entrega`, `codigo_postal_entrega`, `fecha_actualizacion`, `id_usuario_actualizacion` (nueva relación con usuario). FK compuesta `(id_direccion, id_usuario)` en lugar de dos FK independientes. Valores de `estado` definidos. |
| detalle_pedido | `id_variante` pasa de **opcional a obligatoria**; FK compuesta. `subtotal` es columna generada. + `UNIQUE (id_pedido, id_variante)`. |
| movimiento_inventario | + `id_pedido` (FK opcional, nueva relación con detalle_pedido), `stock_anterior`, `stock_nuevo`. Valores de `tipo` definidos. |

### 11.2 Respecto al diagrama de clases (§7.11)

- `Usuario.estado`, `Categoria.estado`, `Producto.estado` → `activo` (los métodos `activar()/desactivar()` y `cambiarEstado()` operan sobre `activo`).
- Cardinalidad `Usuario` — `Carrito`: de `1 : 0..1` a `1 : 0..*` con **máximo un carrito abierto**.
- `VarianteProducto` es obligatoria en `DetalleCarrito` y `DetallePedido` (multiplicidad `0..1` → `1`).
- Atributos nuevos: `Categoria.fechaCreacion`, `VarianteProducto.stockMinimo`, `Pedido` (copia de entrega, `fechaActualizacion`, `usuarioActualizacion`), `MovimientoInventario` (`pedido`, `stockAnterior`, `stockNuevo`).
- `VarianteProducto.actualizarStock(cantidad, tipo)` debe implementarse en el DAO de inventario siguiendo §8 (no en un trigger).
- `DetallePedido.calcularSubtotal()` puede leer la columna generada.

### 11.3 Respecto al documento "Entrega 1" (§7.5 y otros)

- §7.5 dice que la variante existe "solo cuando el artículo lo requiera": ahora **todo producto tiene al menos una variante** (la base cuando no hay talla/color/compatibilidad). El usuario final no lo percibe.
- §7.5 "id_variante (FK opcional)" en DetallePedido y DetalleCarrito: ahora obligatoria.
- RNF08 indica hash "administrado por el proveedor": el hash lo genera Flask; no se usa Neon Auth ni un servicio externo.
- HU12 ("fecha de actualización disponible") y RNF16 (usuario responsable) quedan cubiertos por `pedido.fecha_actualizacion` e `id_usuario_actualizacion` (solo el último cambio).
- RF-34 / HU23 ("umbral configurado"): umbral por variante en `variante_producto.stock_minimo`.
- Estados del pedido: `pendiente`, `confirmado`, `en_preparacion`, `enviado`, `entregado`, `cancelado`.

## 12. Índices

Los índices de PK y UNIQUE (`uq_usuario_correo`, `uq_producto_referencia`, `uq_variante_producto_sku`, etc.) los crea PostgreSQL automáticamente y no se duplican.

| Índice | Consulta que atiende |
|---|---|
| `uq_categoria_nombre_ci` (único, `lower(nombre)`) | Unicidad sin mayúsculas; búsqueda de categoría por nombre |
| `ix_direccion_id_usuario` | Direcciones de un usuario (RF-11) |
| `ux_direccion_principal_activa` (único parcial) | Regla de dirección principal; obtener la principal |
| `ix_producto_id_categoria` | Filtrar por categoría (RF-04) |
| `ix_producto_nombre_lower` (`text_pattern_ops`) | Búsqueda por prefijo del nombre sin mayúsculas (RF-03) |
| `uq_variante_producto_combinacion` (de la restricción) | Variantes de un producto (columna inicial `id_producto`) |
| `ix_variante_producto_stock_bajo` (parcial `stock < stock_minimo`) | Stock bajo (RF-34) |
| `ix_carrito_id_usuario` | Historial de carritos; FK |
| `ux_carrito_abierto_por_usuario` (único parcial) | Regla y búsqueda del carrito abierto |
| `ux_detalle_carrito_linea_activa` (único parcial) | Regla de línea única; líneas activas del carrito |
| `ix_pedido_id_usuario_fecha` | Historial del cliente (RF-20) |
| `ix_pedido_estado_fecha` | Bandeja de pedidos por estado (RF-32) |
| `ix_pedido_fecha` | Resumen por rango de fechas (RF-35) |
| `uq_detalle_pedido_pedido_variante` (de la restricción) | Detalle de un pedido |
| `ix_movimiento_inventario_variante_fecha` | Kárdex por variante |
| `ix_movimiento_inventario_usuario_fecha` | Movimientos por empleado |
| `ix_movimiento_inventario_fecha` | Movimientos por periodo |

La búsqueda "contiene" (`ILIKE '%texto%'`) no usa índices B-tree; con un catálogo pequeño el recorrido secuencial es suficiente. Si el catálogo crece, considerar la extensión `pg_trgm` con un índice GIN (requiere aprobación).

## 13. Seguridad

- Sin credenciales, contraseñas, cadenas de conexión ni datos personales en los archivos.
- No se crea ningún usuario administrador ni contraseña predeterminada. **Primer administrador:** registrarse como cliente por la aplicación y luego, desde el SQL Editor, `UPDATE usuario SET rol = 'administrador' WHERE correo = '<correo>';`.
- Contraseñas: solo hashes generados por Flask; el `CHECK` de longitud es una barrera mínima, no una garantía.
- `REVOKE ALL ... FROM PUBLIC` explícito sobre las 10 tablas. No se crean roles de PostgreSQL.
- React nunca se conecta a PostgreSQL; la cadena de conexión vive solo en variables de entorno de Render (`DATABASE_URL`), con `sslmode=require`.
- Toda consulta del DAO debe ser **parametrizada** (Psycopg 3: `cur.execute("... WHERE correo = %s", (correo,))`). Nunca concatenar texto del usuario en SQL. Para identificadores dinámicos (ordenar por columna), usar listas blancas o `psycopg.sql.Identifier`.
- Los errores de la base (`23505`, `23503`, `23514`, `23001`) deben traducirse a mensajes de negocio sin exponer detalles técnicos (RNF-18).
- Autorización por rol y por propiedad (un cliente solo accede a sus pedidos, carritos y direcciones: filtrar siempre por el `id_usuario` de la sesión — RNF09).

## 14. Responsabilidades del backend

1. Autenticación (hash y verificación), sesión/token, cierre de sesión, comprobación de `usuario.activo`.
2. Autorización por rol y por propiedad de los recursos.
3. Normalización de entradas: correo (minúsculas), referencia y SKU (mayúsculas), recorte de espacios, `NULL` en lugar de cadenas vacías para talla/color/compatibilidad.
4. Crear producto + variante(s) en una transacción.
5. Cálculo del carrito con precios vigentes (RF-15).
6. Protocolos transaccionales de §8 (registro de pedido, cancelación, movimientos manuales).
7. Transiciones de estado según §7, registrando fecha y responsable.
8. Copia de la dirección y del precio al crear el pedido.
9. Filtros de visibilidad (`activo`) en el catálogo y listados.
10. Generación de PDF y envío de correos a partir de las consultas (fuera del alcance de la base).
11. Rol de conexión de mínimo privilegio antes de producción (pendiente, §17).

## 15. Consultas de referencia para la capa DAO

Sirven como base para las "al menos diez consultas" del proyecto y para reportes/gráficos. Usar parámetros (`%s` en Psycopg).

```sql
-- C1. Catálogo público (RF-01, RF-02): productos activos de categorías activas con disponibilidad
SELECT p.id_producto, p.nombre, p.referencia, p.precio, p.imagen, c.nombre AS categoria,
       SUM(v.stock) AS disponible
FROM producto p
JOIN categoria c          ON c.id_categoria = p.id_categoria AND c.activo
JOIN variante_producto v  ON v.id_producto = p.id_producto AND v.activo
WHERE p.activo
GROUP BY p.id_producto, c.nombre
ORDER BY p.nombre;

-- C2. Búsqueda por nombre o referencia (RF-03)
... WHERE p.activo AND (lower(p.nombre) LIKE lower(%s) || '%%' OR p.referencia = upper(%s));

-- C3. Filtro por categoría (RF-04): ... AND p.id_categoria = %s

-- C4. Detalle de producto con variantes (RF-05)
SELECT v.id_variante, v.talla, v.color, v.compatibilidad, v.sku, v.stock
FROM variante_producto v WHERE v.id_producto = %s AND v.activo ORDER BY v.talla, v.color;

-- C5. Carrito con subtotales y total (RF-15)
SELECT dc.id_detalle_carrito, p.nombre, v.talla, v.color, dc.cantidad, p.precio,
       dc.cantidad * p.precio AS subtotal,
       SUM(dc.cantidad * p.precio) OVER () AS total
FROM carrito ca
JOIN detalle_carrito dc   ON dc.id_carrito = ca.id_carrito AND dc.activo
JOIN producto p           ON p.id_producto = dc.id_producto
JOIN variante_producto v  ON v.id_variante = dc.id_variante
WHERE ca.id_usuario = %s AND ca.estado = 'abierto' AND ca.activo;

-- C6. Historial de pedidos del cliente (RF-20, RF-21)
SELECT id_pedido, fecha, estado, total, fecha_actualizacion
FROM pedido WHERE id_usuario = %s AND activo ORDER BY fecha DESC;

-- C7. Bandeja de pedidos por estado (RF-32)
SELECT pe.id_pedido, pe.fecha, u.nombre || ' ' || u.apellido AS cliente, pe.total, pe.estado
FROM pedido pe JOIN usuario u ON u.id_usuario = pe.id_usuario
WHERE pe.estado = %s AND pe.activo ORDER BY pe.fecha;

-- C8. Detalle de un pedido (RF-32, HU22)
SELECT d.id_detalle, p.nombre, p.referencia, v.talla, v.color, v.sku,
       d.cantidad, d.precio_unitario, d.subtotal
FROM detalle_pedido d
JOIN producto p ON p.id_producto = d.id_producto
JOIN variante_producto v ON v.id_variante = d.id_variante
WHERE d.id_pedido = %s ORDER BY d.id_detalle;

-- C9. Stock bajo (RF-34)
SELECT p.nombre, p.referencia, v.sku, v.talla, v.color, v.stock, v.stock_minimo
FROM variante_producto v JOIN producto p ON p.id_producto = v.id_producto
WHERE v.activo AND p.activo AND v.stock < v.stock_minimo
ORDER BY v.stock - v.stock_minimo;

-- C10. Resumen de pedidos por rango de fechas (RF-35); fechas de Colombia
SELECT (fecha AT TIME ZONE 'America/Bogota')::date AS dia,
       COUNT(*) AS pedidos,
       COALESCE(SUM(total) FILTER (WHERE estado <> 'cancelado'), 0) AS ventas
FROM pedido
WHERE fecha >= (%s::date)::timestamp AT TIME ZONE 'America/Bogota'
  AND fecha <  ((%s::date) + 1)::timestamp AT TIME ZONE 'America/Bogota'
GROUP BY 1 ORDER BY 1;

-- C11. Productos más vendidos (gráfico)
SELECT p.nombre, SUM(d.cantidad) AS unidades, SUM(d.subtotal) AS valor
FROM detalle_pedido d
JOIN pedido pe ON pe.id_pedido = d.id_pedido AND pe.estado <> 'cancelado'
JOIN producto p ON p.id_producto = d.id_producto
GROUP BY p.nombre ORDER BY unidades DESC LIMIT 10;

-- C12. Kárdex de una variante (trazabilidad)
SELECT m.fecha, m.tipo, m.cantidad, m.stock_anterior, m.stock_nuevo, m.motivo,
       m.id_pedido, u.nombre || ' ' || u.apellido AS responsable
FROM movimiento_inventario m JOIN usuario u ON u.id_usuario = m.id_usuario
WHERE m.id_variante = %s ORDER BY m.fecha, m.id_movimiento;

-- C13. Pedidos por estado (gráfico de torta)
SELECT estado, COUNT(*) FROM pedido WHERE activo GROUP BY estado;
```

## 16. Futuras migraciones

- No modificar `schema.sql` una vez ejecutado en producción. Cada cambio posterior va en un archivo nuevo y numerado, por ejemplo `database/migrations/V002__descripcion.sql`, también dentro de `BEGIN … COMMIT`.
- Probar cada migración primero en una **rama de Neon** creada desde `production` (las ramas son copias aisladas y baratas), nunca directamente en `production`.
- Agregar columnas `NOT NULL` en dos pasos (agregar con `DEFAULT` o como nula → poblar → `SET NOT NULL`).
- Para nuevas restricciones sobre tablas con datos, usar `ADD CONSTRAINT ... NOT VALID` y luego `VALIDATE CONSTRAINT`.
- Crear índices en tablas grandes con `CREATE INDEX CONCURRENTLY` (fuera de una transacción).
- Registrar en este README la versión del esquema y el cambio. Si el número de migraciones crece, evaluar una herramienta (Alembic, Flyway) o una tabla de control de versiones (requiere aprobación por ser una tabla adicional).

## 17. Limitaciones y decisiones pendientes

- **O6 — Rol de mínimo privilegio para Flask** (pendiente, antes de conectar el backend a producción). Propuesta: rol `fullbikers_app` con `SELECT, INSERT, UPDATE` sobre las tablas (sin `DELETE`, `TRUNCATE` ni DDL) y `USAGE` sobre las secuencias de identidad; el owner solo para migraciones.
- **Invariantes no declarativas** (las garantiza el backend; detectables con `verification.sql`): producto con al menos una variante; pedido con al menos una línea; `pedido.subtotal = Σ líneas`; cantidad del movimiento igual a la de la línea; copia de entrega igual a la dirección al momento del pedido; transiciones de estado válidas; continuidad de la cadena `stock_anterior`/`stock_nuevo`.
- **Historial de estados:** solo se guarda el último cambio. Si se requiere trazabilidad completa (quién confirmó, quién envió), habrá que crear `historial_estado_pedido` (tabla 11, requiere aprobación).
- **Datos del producto en el pedido:** se conserva el precio; nombre y referencia se leen del producto actual. Si un producto se renombra, los pedidos antiguos mostrarán el nombre nuevo.
- **Total del pedido:** hoy igual al subtotal. Envío, impuestos o descuentos requerirían nuevas columnas.
- **Imágenes:** un solo campo `imagen` por producto (RF-26). Galería de imágenes = tabla adicional (requiere aprobación).
- **Búsqueda "contiene"** sin índice (ver §12).
- **Validación de formatos:** correo, teléfono y código postal se validan de forma básica; la validación completa corresponde a Flask.
- **Cliente que cancela:** se propone que solo cancele en estado `pendiente`; ajustable en el backend sin cambiar el esquema.
- **Compatibilidad con el SQL Editor de Neon:** el script usa `BEGIN/COMMIT` y un bloque `DO`; se probó con `psql`, no en el editor web.

## 18. Pruebas realizadas

Pruebas **ejecutadas realmente** el 2026-11-24 en un clúster PostgreSQL **18.4** local, temporal y aislado (creado con `initdb` en un directorio temporal, puerto 55432, solo `localhost`; eliminado al terminar). **No** se usó Neon ni el servicio PostgreSQL instalado en el equipo.

| Prueba | Resultado |
|---|---|
| `schema.sql` sobre base vacía (`psql -v ON_ERROR_STOP=1`) | ✅ `COMMIT`, sin errores |
| Segunda ejecución sobre la base ya creada | ✅ Falla con `relation "usuario" already exists` y no crea nada |
| `verification.sql` | ✅ Sin errores: 10 tablas, ≥ 5 atributos, 10 PK, 13 FK `RESTRICT`, 8 UNIQUE, 4 índices únicos parciales/expresión, 44 CHECK, 33 índices, `activo` correcto en 10/10, 0 triggers, 0 permisos a PUBLIC, consultas de integridad 14–19 en 0 filas |
| Batería de 94 casos válidos e inválidos (usuarios, direcciones, categorías, productos, variantes, carrito, pedido, detalle, movimientos, FK restrictivas, catálogo, stock bajo, flujo completo de pedido, confirmación, cancelación, doble cancelación, devolución duplicada, histórico de precio y dirección, borrado lógico de movimientos) | ✅ 94/94 con el resultado y SQLSTATE esperados |
| Concurrencia: dos sesiones compran la última unidad a la vez | ✅ La primera la obtiene; la segunda espera el bloqueo de fila (~2 s), no afecta filas y el stock termina en 0 |

**Pendiente** (lo ejecuta el equipo): `schema.sql` y `verification.sql` en Neon `production` (PostgreSQL 18.7) desde el SQL Editor.
