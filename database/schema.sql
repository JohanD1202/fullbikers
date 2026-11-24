-- =============================================================================
-- FullBikers - Esquema inicial de base de datos
-- -----------------------------------------------------------------------------
-- Proyecto      : FullBikers - Tienda virtual B2C de accesorios para motociclistas
-- Asignatura    : Desarrollo de Software I - Universidad del Valle (Sede Tuluá)
-- Motor         : PostgreSQL 18 (objetivo: 18.7 en Neon). Requiere >= 15 por
--                 el uso de UNIQUE NULLS NOT DISTINCT.
-- Base de datos : fullbikers (ya existente; este script NO la crea)
-- Esquema       : public
-- Versión       : 1.0.0 (esquema inicial)
-- Fecha         : 2026-11-24
--
-- Ejecución     : manual, desde el SQL Editor de Neon, sobre una base VACÍA.
--                 Todo el script se ejecuta en una sola transacción: si algo
--                 falla (por ejemplo, porque una tabla ya existe), no se crea
--                 nada.
--
-- Principios    :
--   * Sin DROP, TRUNCATE ni CREATE ... IF NOT EXISTS: si existe un esquema
--     previo incompatible, el script falla de forma segura.
--   * Sin triggers ni funciones: las invariantes que pueden expresarse
--     declarativamente se garantizan con PK, FK, UNIQUE y CHECK; la lógica de
--     negocio (transiciones de estado, movimientos de inventario, cálculo de
--     totales) se implementa en el backend Flask (MVC + DAO).
--   * Borrado lógico mediante la columna "activo" en las diez tablas.
--   * Claves foráneas restrictivas (ON DELETE/UPDATE RESTRICT): nunca se
--     eliminan físicamente datos históricos en cascada.
--   * Sin credenciales, cadenas de conexión ni datos de prueba.
--
-- Documentación completa: database/README.md
-- =============================================================================

BEGIN;

SET LOCAL search_path TO public;
SET LOCAL lock_timeout = '10s';

-- -----------------------------------------------------------------------------
-- Verificación previa: versión mínima del servidor
-- (UNIQUE NULLS NOT DISTINCT existe desde PostgreSQL 15).
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF current_setting('server_version_num')::int < 150000 THEN
        RAISE EXCEPTION 'FullBikers requiere PostgreSQL 15 o superior (versión actual: %)',
            current_setting('server_version');
    END IF;
END
$$;


-- =============================================================================
-- 1. usuario
-- =============================================================================
CREATE TABLE usuario (
    id_usuario       INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre           VARCHAR(80)  NOT NULL,
    apellido         VARCHAR(80)  NOT NULL,
    correo           VARCHAR(254) NOT NULL,
    contrasena_hash  VARCHAR(255) NOT NULL,
    telefono         VARCHAR(20),
    rol              VARCHAR(20)  NOT NULL DEFAULT 'cliente',
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    fecha_registro   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_usuario PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuario_correo UNIQUE (correo),
    CONSTRAINT ck_usuario_nombre_no_vacio   CHECK (btrim(nombre) <> ''),
    CONSTRAINT ck_usuario_apellido_no_vacio CHECK (btrim(apellido) <> ''),
    CONSTRAINT ck_usuario_correo_normalizado CHECK (correo = lower(btrim(correo))),
    CONSTRAINT ck_usuario_correo_formato    CHECK (correo ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    CONSTRAINT ck_usuario_contrasena_hash_longitud CHECK (char_length(contrasena_hash) >= 20),
    CONSTRAINT ck_usuario_telefono_formato  CHECK (telefono IS NULL OR telefono ~ '^\+?[0-9][0-9 ()-]{5,18}[0-9]$'),
    CONSTRAINT ck_usuario_rol CHECK (rol IN ('cliente', 'empleado', 'administrador'))
);

COMMENT ON TABLE  usuario IS 'Personas que acceden al sistema (clientes, empleados y administradores). La autorización por rol se implementa en Flask.';
COMMENT ON COLUMN usuario.id_usuario      IS 'Identificador interno generado por la base de datos.';
COMMENT ON COLUMN usuario.nombre          IS 'Nombre(s) del usuario.';
COMMENT ON COLUMN usuario.apellido        IS 'Apellido(s) del usuario.';
COMMENT ON COLUMN usuario.correo          IS 'Correo de acceso. Único y almacenado normalizado (minúsculas, sin espacios extremos); el backend debe normalizar antes de insertar y de consultar.';
COMMENT ON COLUMN usuario.contrasena_hash IS 'Hash de la contraseña generado por Flask (p. ej. scrypt/argon2/bcrypt). Nunca texto plano.';
COMMENT ON COLUMN usuario.telefono        IS 'Teléfono de contacto como texto (admite +, espacios, guiones y paréntesis). Opcional.';
COMMENT ON COLUMN usuario.rol             IS 'Rol de aplicación: cliente (predeterminado), empleado o administrador. No sustituye la autorización del backend.';
COMMENT ON COLUMN usuario.activo          IS 'Borrado lógico. FALSE = cuenta desactivada (no puede iniciar sesión). Sustituye al atributo "estado" del MER.';
COMMENT ON COLUMN usuario.fecha_registro  IS 'Instante de registro (TIMESTAMPTZ; mostrar en America/Bogota).';


-- =============================================================================
-- 2. direccion
-- =============================================================================
CREATE TABLE direccion (
    id_direccion   INTEGER GENERATED ALWAYS AS IDENTITY,
    id_usuario     INTEGER      NOT NULL,
    departamento   VARCHAR(60)  NOT NULL,
    municipio      VARCHAR(80)  NOT NULL,
    direccion      VARCHAR(150) NOT NULL,
    complemento    VARCHAR(100),
    codigo_postal  VARCHAR(10),
    principal      BOOLEAN      NOT NULL DEFAULT FALSE,
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_direccion PRIMARY KEY (id_direccion),
    -- Clave alterna usada por la FK compuesta de pedido (la dirección debe
    -- pertenecer al mismo usuario que realiza el pedido).
    CONSTRAINT uq_direccion_id_usuario UNIQUE (id_direccion, id_usuario),
    CONSTRAINT fk_direccion_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_direccion_departamento_no_vacio CHECK (btrim(departamento) <> ''),
    CONSTRAINT ck_direccion_municipio_no_vacio    CHECK (btrim(municipio) <> ''),
    CONSTRAINT ck_direccion_direccion_no_vacia    CHECK (btrim(direccion) <> ''),
    CONSTRAINT ck_direccion_codigo_postal_formato CHECK (codigo_postal IS NULL OR codigo_postal ~ '^[0-9]{4,10}$'),
    -- Una dirección inactiva no puede seguir marcada como principal.
    CONSTRAINT ck_direccion_principal_activa CHECK (activo OR NOT principal)
);

COMMENT ON TABLE  direccion IS 'Direcciones de entrega registradas por los usuarios. Un usuario puede tener varias y como máximo una principal activa.';
COMMENT ON COLUMN direccion.id_direccion  IS 'Identificador interno de la dirección.';
COMMENT ON COLUMN direccion.id_usuario    IS 'Usuario propietario de la dirección.';
COMMENT ON COLUMN direccion.departamento  IS 'Departamento de Colombia.';
COMMENT ON COLUMN direccion.municipio     IS 'Municipio o ciudad.';
COMMENT ON COLUMN direccion.direccion     IS 'Dirección (calle, carrera, número).';
COMMENT ON COLUMN direccion.complemento   IS 'Información adicional: apartamento, barrio, referencias. Opcional.';
COMMENT ON COLUMN direccion.codigo_postal IS 'Código postal como texto (en Colombia, 6 dígitos). Opcional.';
COMMENT ON COLUMN direccion.principal     IS 'TRUE si es la dirección predeterminada del usuario (máximo una activa por usuario).';
COMMENT ON COLUMN direccion.activo        IS 'Borrado lógico. Los pedidos conservan una copia histórica, por lo que desactivar o editar no altera pedidos previos.';


-- =============================================================================
-- 3. categoria
-- =============================================================================
CREATE TABLE categoria (
    id_categoria    INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre          VARCHAR(60) NOT NULL,
    descripcion     TEXT,
    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_categoria PRIMARY KEY (id_categoria),
    CONSTRAINT ck_categoria_nombre_normalizado CHECK (nombre = btrim(nombre) AND nombre <> '')
);

-- Unicidad del nombre sin distinguir mayúsculas/minúsculas ("Cascos" = "cascos").
-- Se usa un índice único por expresión porque una restricción UNIQUE no admite
-- expresiones; conserva la capitalización original para mostrarla en la tienda.
CREATE UNIQUE INDEX uq_categoria_nombre_ci ON categoria (lower(nombre));

COMMENT ON TABLE  categoria IS 'Agrupación de productos (cascos, guantes, chaquetas, repuestos, accesorios...).';
COMMENT ON COLUMN categoria.id_categoria   IS 'Identificador interno de la categoría.';
COMMENT ON COLUMN categoria.nombre         IS 'Nombre visible. Único sin distinguir mayúsculas (índice uq_categoria_nombre_ci).';
COMMENT ON COLUMN categoria.descripcion    IS 'Descripción opcional de la categoría.';
COMMENT ON COLUMN categoria.activo         IS 'Borrado lógico. Una categoría inactiva oculta sus productos del catálogo público. Sustituye al atributo "estado" del MER.';
COMMENT ON COLUMN categoria.fecha_creacion IS 'Instante de creación. Atributo agregado para cumplir el mínimo de cinco atributos por tabla.';


-- =============================================================================
-- 4. producto
-- =============================================================================
CREATE TABLE producto (
    id_producto   INTEGER GENERATED ALWAYS AS IDENTITY,
    id_categoria  INTEGER       NOT NULL,
    nombre        VARCHAR(150)  NOT NULL,
    referencia    VARCHAR(50)   NOT NULL,
    descripcion   TEXT,
    marca         VARCHAR(80),
    precio        NUMERIC(14,2) NOT NULL,
    imagen        VARCHAR(500),
    activo        BOOLEAN       NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_producto PRIMARY KEY (id_producto),
    CONSTRAINT uq_producto_referencia UNIQUE (referencia),
    CONSTRAINT fk_producto_categoria FOREIGN KEY (id_categoria)
        REFERENCES categoria (id_categoria) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_producto_nombre_no_vacio CHECK (btrim(nombre) <> ''),
    CONSTRAINT ck_producto_referencia_normalizada CHECK (referencia = upper(btrim(referencia)) AND referencia <> ''),
    CONSTRAINT ck_producto_marca_no_vacia  CHECK (marca IS NULL OR btrim(marca) <> ''),
    CONSTRAINT ck_producto_precio_no_negativo CHECK (precio >= 0),
    CONSTRAINT ck_producto_imagen_no_vacia CHECK (imagen IS NULL OR btrim(imagen) <> '')
);

COMMENT ON TABLE  producto IS 'Información comercial de cada artículo. El inventario NO se guarda aquí: vive en variante_producto (todo producto tiene al menos una variante, la "variante base" si no tiene talla/color/compatibilidad).';
COMMENT ON COLUMN producto.id_producto  IS 'Identificador interno del producto.';
COMMENT ON COLUMN producto.id_categoria IS 'Categoría a la que pertenece el producto.';
COMMENT ON COLUMN producto.nombre       IS 'Nombre comercial.';
COMMENT ON COLUMN producto.referencia   IS 'Referencia comercial única, almacenada en MAYÚSCULAS y sin espacios extremos.';
COMMENT ON COLUMN producto.descripcion  IS 'Descripción y características (certificaciones, materiales, etc.).';
COMMENT ON COLUMN producto.marca        IS 'Marca del fabricante. Opcional.';
COMMENT ON COLUMN producto.precio       IS 'Precio vigente en COP. Los pedidos guardan su propio precio_unitario, por lo que cambiar este valor no altera pedidos anteriores.';
COMMENT ON COLUMN producto.imagen       IS 'URL o ruta de almacenamiento de la imagen principal (no el binario).';
COMMENT ON COLUMN producto.activo       IS 'Borrado lógico. Inactivo = no visible en el catálogo público. Sustituye al atributo "estado" del MER.';


-- =============================================================================
-- 5. variante_producto
-- =============================================================================
CREATE TABLE variante_producto (
    id_variante     INTEGER GENERATED ALWAYS AS IDENTITY,
    id_producto     INTEGER      NOT NULL,
    talla           VARCHAR(20),
    color           VARCHAR(40),
    compatibilidad  VARCHAR(150),
    sku             VARCHAR(60)  NOT NULL,
    stock           INTEGER      NOT NULL DEFAULT 0,
    stock_minimo    INTEGER      NOT NULL DEFAULT 5,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_variante_producto PRIMARY KEY (id_variante),
    CONSTRAINT uq_variante_producto_sku UNIQUE (sku),
    -- Clave alterna usada por las FK compuestas de detalle_carrito y
    -- detalle_pedido (garantiza que la variante pertenece al producto).
    CONSTRAINT uq_variante_producto_id_producto UNIQUE (id_variante, id_producto),
    -- Evita combinaciones duplicadas; NULL se considera igual a NULL, por lo
    -- que un producto no puede tener dos variantes base.
    CONSTRAINT uq_variante_producto_combinacion
        UNIQUE NULLS NOT DISTINCT (id_producto, talla, color, compatibilidad),
    CONSTRAINT fk_variante_producto_producto FOREIGN KEY (id_producto)
        REFERENCES producto (id_producto) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_variante_producto_talla_no_vacia          CHECK (talla IS NULL OR btrim(talla) <> ''),
    CONSTRAINT ck_variante_producto_color_no_vacio          CHECK (color IS NULL OR btrim(color) <> ''),
    CONSTRAINT ck_variante_producto_compatibilidad_no_vacia CHECK (compatibilidad IS NULL OR btrim(compatibilidad) <> ''),
    CONSTRAINT ck_variante_producto_sku_normalizado CHECK (sku = upper(sku) AND sku ~ '^[A-Z0-9][A-Z0-9._/-]*$'),
    CONSTRAINT ck_variante_producto_stock_no_negativo        CHECK (stock >= 0),
    CONSTRAINT ck_variante_producto_stock_minimo_no_negativo CHECK (stock_minimo >= 0)
);

COMMENT ON TABLE  variante_producto IS 'Presentaciones de un producto (talla, color, compatibilidad) y su existencia. Única fuente del stock. Un producto sin características tiene una variante base con talla, color y compatibilidad en NULL.';
COMMENT ON COLUMN variante_producto.id_variante    IS 'Identificador interno de la variante.';
COMMENT ON COLUMN variante_producto.id_producto    IS 'Producto al que pertenece la variante.';
COMMENT ON COLUMN variante_producto.talla          IS 'Talla (S, M, L, 58...). NULL si no aplica.';
COMMENT ON COLUMN variante_producto.color          IS 'Color. NULL si no aplica.';
COMMENT ON COLUMN variante_producto.compatibilidad IS 'Motocicletas o modelos compatibles. NULL si no aplica.';
COMMENT ON COLUMN variante_producto.sku            IS 'Código único de inventario, en MAYÚSCULAS, sin espacios (A-Z, 0-9, . _ / -).';
COMMENT ON COLUMN variante_producto.stock          IS 'Existencia actual. Nunca negativa. Solo debe modificarla el DAO de inventario junto con el registro de movimiento_inventario, en la misma transacción.';
COMMENT ON COLUMN variante_producto.stock_minimo   IS 'Umbral de stock bajo configurable por el administrador (RF-34). Predeterminado: 5.';
COMMENT ON COLUMN variante_producto.activo         IS 'Borrado lógico. Variante inactiva = no se puede agregar al carrito ni vender.';


-- =============================================================================
-- 6. carrito
-- =============================================================================
CREATE TABLE carrito (
    id_carrito      INTEGER GENERATED ALWAYS AS IDENTITY,
    id_usuario      INTEGER     NOT NULL,
    fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado          VARCHAR(20) NOT NULL DEFAULT 'abierto',
    activo          BOOLEAN     NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_carrito PRIMARY KEY (id_carrito),
    CONSTRAINT fk_carrito_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_carrito_estado CHECK (estado IN ('abierto', 'convertido', 'abandonado'))
);

COMMENT ON TABLE  carrito IS 'Carrito de compras de un usuario. Se conservan los carritos convertidos y abandonados; como máximo uno abierto y activo por usuario.';
COMMENT ON COLUMN carrito.id_carrito     IS 'Identificador interno del carrito.';
COMMENT ON COLUMN carrito.id_usuario     IS 'Usuario propietario del carrito.';
COMMENT ON COLUMN carrito.fecha_creacion IS 'Instante de creación del carrito.';
COMMENT ON COLUMN carrito.estado         IS 'Estado operativo: abierto (inicial), convertido (generó un pedido) o abandonado.';
COMMENT ON COLUMN carrito.activo         IS 'Borrado lógico, independiente del estado operativo.';


-- =============================================================================
-- 7. detalle_carrito
-- =============================================================================
CREATE TABLE detalle_carrito (
    id_detalle_carrito  INTEGER GENERATED ALWAYS AS IDENTITY,
    id_carrito          INTEGER NOT NULL,
    id_producto         INTEGER NOT NULL,
    id_variante         INTEGER NOT NULL,
    cantidad            INTEGER NOT NULL,
    activo              BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_detalle_carrito PRIMARY KEY (id_detalle_carrito),
    CONSTRAINT fk_detalle_carrito_carrito FOREIGN KEY (id_carrito)
        REFERENCES carrito (id_carrito) ON UPDATE RESTRICT ON DELETE RESTRICT,
    -- FK compuesta: implementa las relaciones "se_agrega_en" (producto) y
    -- "especifica" (variante) del MER y garantiza que la variante pertenece
    -- al producto indicado.
    CONSTRAINT fk_detalle_carrito_variante_producto FOREIGN KEY (id_variante, id_producto)
        REFERENCES variante_producto (id_variante, id_producto) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_detalle_carrito_cantidad_positiva CHECK (cantidad > 0)
);

COMMENT ON TABLE  detalle_carrito IS 'Líneas del carrito. No descuentan stock; el precio se toma del producto vigente al calcular (RF-15).';
COMMENT ON COLUMN detalle_carrito.id_detalle_carrito IS 'Identificador interno de la línea.';
COMMENT ON COLUMN detalle_carrito.id_carrito         IS 'Carrito al que pertenece la línea.';
COMMENT ON COLUMN detalle_carrito.id_producto        IS 'Producto seleccionado (redundancia controlada por la FK compuesta con la variante).';
COMMENT ON COLUMN detalle_carrito.id_variante        IS 'Variante seleccionada. Obligatoria (variante base si el producto no tiene características).';
COMMENT ON COLUMN detalle_carrito.cantidad           IS 'Unidades seleccionadas (> 0).';
COMMENT ON COLUMN detalle_carrito.activo             IS 'Borrado lógico: retirar un artículo del carrito (RF-14) lo desactiva.';


-- =============================================================================
-- 8. pedido
-- =============================================================================
CREATE TABLE pedido (
    id_pedido                 INTEGER GENERATED ALWAYS AS IDENTITY,
    id_usuario                INTEGER       NOT NULL,
    id_direccion              INTEGER       NOT NULL,
    fecha                     TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado                    VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
    subtotal                  NUMERIC(14,2) NOT NULL,
    total                     NUMERIC(14,2) NOT NULL,
    observaciones             TEXT,
    -- Copia histórica de la dirección de entrega (desnormalización intencional).
    departamento_entrega      VARCHAR(60)   NOT NULL,
    municipio_entrega         VARCHAR(80)   NOT NULL,
    direccion_entrega         VARCHAR(150)  NOT NULL,
    complemento_entrega       VARCHAR(100),
    codigo_postal_entrega     VARCHAR(10),
    -- Trazabilidad del último cambio de estado.
    fecha_actualizacion       TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario_actualizacion  INTEGER,
    activo                    BOOLEAN       NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_pedido PRIMARY KEY (id_pedido),
    -- FK compuesta: implementa las relaciones "realiza" (usuario) y
    -- "es_destino_de" (dirección) del MER y garantiza que la dirección
    -- pertenece al mismo usuario que realiza el pedido.
    CONSTRAINT fk_pedido_direccion_usuario FOREIGN KEY (id_direccion, id_usuario)
        REFERENCES direccion (id_direccion, id_usuario) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_pedido_usuario_actualizacion FOREIGN KEY (id_usuario_actualizacion)
        REFERENCES usuario (id_usuario) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_pedido_estado CHECK (estado IN
        ('pendiente', 'confirmado', 'en_preparacion', 'enviado', 'entregado', 'cancelado')),
    CONSTRAINT ck_pedido_subtotal_no_negativo CHECK (subtotal >= 0),
    CONSTRAINT ck_pedido_total_coherente      CHECK (total >= subtotal),
    CONSTRAINT ck_pedido_observaciones_longitud CHECK (observaciones IS NULL OR char_length(observaciones) <= 1000),
    CONSTRAINT ck_pedido_departamento_entrega_no_vacio CHECK (btrim(departamento_entrega) <> ''),
    CONSTRAINT ck_pedido_municipio_entrega_no_vacio    CHECK (btrim(municipio_entrega) <> ''),
    CONSTRAINT ck_pedido_direccion_entrega_no_vacia    CHECK (btrim(direccion_entrega) <> ''),
    CONSTRAINT ck_pedido_fecha_actualizacion CHECK (fecha_actualizacion >= fecha),
    -- Todo cambio de estado posterior al inicial debe registrar su responsable.
    CONSTRAINT ck_pedido_responsable_cambio CHECK (estado = 'pendiente' OR id_usuario_actualizacion IS NOT NULL)
);

COMMENT ON TABLE  pedido IS 'Solicitud de compra de un cliente. Conserva copia histórica de la dirección de entrega y de los precios (en detalle_pedido).';
COMMENT ON COLUMN pedido.id_pedido                IS 'Identificador único del pedido (RF-18), generado por la base de datos.';
COMMENT ON COLUMN pedido.id_usuario               IS 'Cliente que realiza el pedido.';
COMMENT ON COLUMN pedido.id_direccion             IS 'Dirección seleccionada (debe pertenecer al mismo usuario). Referencia; los datos históricos están en las columnas *_entrega.';
COMMENT ON COLUMN pedido.fecha                    IS 'Instante de registro del pedido.';
COMMENT ON COLUMN pedido.estado                   IS 'Estado operativo: pendiente (inicial), confirmado, en_preparacion, enviado, entregado, cancelado. Las transiciones las controla el backend.';
COMMENT ON COLUMN pedido.subtotal                 IS 'Suma de detalle_pedido.subtotal, calculada por el backend en la misma transacción.';
COMMENT ON COLUMN pedido.total                    IS 'Valor total a pagar. Hoy igual al subtotal (no hay envío, impuestos ni descuentos en el alcance); debe ser >= subtotal.';
COMMENT ON COLUMN pedido.observaciones            IS 'Observaciones del cliente (máximo 1000 caracteres).';
COMMENT ON COLUMN pedido.departamento_entrega     IS 'Copia histórica de direccion.departamento al momento del pedido.';
COMMENT ON COLUMN pedido.municipio_entrega        IS 'Copia histórica de direccion.municipio al momento del pedido.';
COMMENT ON COLUMN pedido.direccion_entrega        IS 'Copia histórica de direccion.direccion al momento del pedido.';
COMMENT ON COLUMN pedido.complemento_entrega      IS 'Copia histórica de direccion.complemento al momento del pedido.';
COMMENT ON COLUMN pedido.codigo_postal_entrega    IS 'Copia histórica de direccion.codigo_postal al momento del pedido.';
COMMENT ON COLUMN pedido.fecha_actualizacion      IS 'Instante del último cambio de estado (HU12). Igual a fecha al crear.';
COMMENT ON COLUMN pedido.id_usuario_actualizacion IS 'Usuario responsable del último cambio de estado (RNF16). NULL solo mientras el pedido está pendiente y sin cambios.';
COMMENT ON COLUMN pedido.activo                   IS 'Borrado lógico administrativo. NO equivale a cancelar: la cancelación se expresa con estado = cancelado.';


-- =============================================================================
-- 9. detalle_pedido
-- =============================================================================
CREATE TABLE detalle_pedido (
    id_detalle       INTEGER GENERATED ALWAYS AS IDENTITY,
    id_pedido        INTEGER       NOT NULL,
    id_producto      INTEGER       NOT NULL,
    id_variante      INTEGER       NOT NULL,
    cantidad         INTEGER       NOT NULL,
    precio_unitario  NUMERIC(14,2) NOT NULL,
    subtotal         NUMERIC(14,2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
    activo           BOOLEAN       NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_detalle_pedido PRIMARY KEY (id_detalle),
    -- Una sola línea por variante en cada pedido. También es la clave
    -- referenciada por movimiento_inventario (id_pedido, id_variante).
    CONSTRAINT uq_detalle_pedido_pedido_variante UNIQUE (id_pedido, id_variante),
    CONSTRAINT fk_detalle_pedido_pedido FOREIGN KEY (id_pedido)
        REFERENCES pedido (id_pedido) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_detalle_pedido_variante_producto FOREIGN KEY (id_variante, id_producto)
        REFERENCES variante_producto (id_variante, id_producto) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_detalle_pedido_cantidad_positiva CHECK (cantidad > 0),
    CONSTRAINT ck_detalle_pedido_precio_no_negativo CHECK (precio_unitario >= 0)
);

COMMENT ON TABLE  detalle_pedido IS 'Líneas del pedido con el precio vigente al momento de la compra. Inmutables una vez creadas.';
COMMENT ON COLUMN detalle_pedido.id_detalle      IS 'Identificador interno de la línea.';
COMMENT ON COLUMN detalle_pedido.id_pedido       IS 'Pedido al que pertenece la línea.';
COMMENT ON COLUMN detalle_pedido.id_producto     IS 'Producto vendido (redundancia controlada por la FK compuesta con la variante).';
COMMENT ON COLUMN detalle_pedido.id_variante     IS 'Variante vendida. Obligatoria.';
COMMENT ON COLUMN detalle_pedido.cantidad        IS 'Unidades vendidas (> 0).';
COMMENT ON COLUMN detalle_pedido.precio_unitario IS 'Copia de producto.precio al registrar el pedido (RF-19). No cambia si el precio del producto cambia.';
COMMENT ON COLUMN detalle_pedido.subtotal        IS 'Columna generada: cantidad * precio_unitario. No se puede escribir directamente.';
COMMENT ON COLUMN detalle_pedido.activo          IS 'Borrado lógico. En operación normal siempre TRUE: las líneas de un pedido no se eliminan ni se desactivan.';


-- =============================================================================
-- 10. movimiento_inventario
-- =============================================================================
CREATE TABLE movimiento_inventario (
    id_movimiento   INTEGER GENERATED ALWAYS AS IDENTITY,
    id_variante     INTEGER      NOT NULL,
    id_usuario      INTEGER      NOT NULL,
    id_pedido       INTEGER,
    tipo            VARCHAR(10)  NOT NULL,
    cantidad        INTEGER      NOT NULL,
    stock_anterior  INTEGER      NOT NULL,
    stock_nuevo     INTEGER      NOT NULL,
    fecha           TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motivo          VARCHAR(255) NOT NULL,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_movimiento_inventario PRIMARY KEY (id_movimiento),
    CONSTRAINT fk_movimiento_inventario_variante FOREIGN KEY (id_variante)
        REFERENCES variante_producto (id_variante) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_movimiento_inventario_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario) ON UPDATE RESTRICT ON DELETE RESTRICT,
    -- FK compuesta opcional (MATCH SIMPLE: solo se verifica si id_pedido no es
    -- NULL): un movimiento asociado a un pedido debe corresponder a una línea
    -- real de ese pedido con la misma variante.
    CONSTRAINT fk_movimiento_inventario_detalle_pedido FOREIGN KEY (id_pedido, id_variante)
        REFERENCES detalle_pedido (id_pedido, id_variante) ON UPDATE RESTRICT ON DELETE RESTRICT,
    -- Como máximo una salida (venta) y una entrada (devolución por cancelación)
    -- por pedido y variante: impide descuentos o devoluciones duplicadas.
    -- Los movimientos manuales (id_pedido NULL) no se ven afectados.
    CONSTRAINT uq_movimiento_inventario_pedido_variante_tipo UNIQUE (id_pedido, id_variante, tipo),
    CONSTRAINT ck_movimiento_inventario_tipo CHECK (tipo IN ('entrada', 'salida', 'ajuste')),
    -- entrada/salida: cantidad positiva. ajuste: diferencia con signo, distinta
    -- de cero (no se permiten movimientos sin efecto).
    CONSTRAINT ck_movimiento_inventario_cantidad_tipo CHECK (
        (tipo IN ('entrada', 'salida') AND cantidad > 0)
        OR (tipo = 'ajuste' AND cantidad <> 0)
    ),
    CONSTRAINT ck_movimiento_inventario_stock_anterior_no_negativo CHECK (stock_anterior >= 0),
    CONSTRAINT ck_movimiento_inventario_stock_nuevo_no_negativo    CHECK (stock_nuevo >= 0),
    CONSTRAINT ck_movimiento_inventario_stock_coherente CHECK (
        stock_nuevo = stock_anterior + CASE WHEN tipo = 'salida' THEN -cantidad ELSE cantidad END
    ),
    -- Los ajustes son correcciones manuales: no se asocian a pedidos.
    CONSTRAINT ck_movimiento_inventario_ajuste_sin_pedido CHECK (tipo <> 'ajuste' OR id_pedido IS NULL),
    CONSTRAINT ck_movimiento_inventario_motivo_no_vacio CHECK (btrim(motivo) <> '')
);

COMMENT ON TABLE  movimiento_inventario IS 'Bitácora inmutable de entradas, salidas y ajustes de inventario. Cada fila se inserta en la misma transacción que actualiza variante_producto.stock. Las correcciones se hacen con un nuevo ajuste, nunca editando o desactivando movimientos.';
COMMENT ON COLUMN movimiento_inventario.id_movimiento  IS 'Identificador interno del movimiento.';
COMMENT ON COLUMN movimiento_inventario.id_variante    IS 'Variante cuyo stock se afectó.';
COMMENT ON COLUMN movimiento_inventario.id_usuario     IS 'Usuario responsable: el empleado/administrador en movimientos manuales; el cliente en la salida por venta; quien cancela en la devolución.';
COMMENT ON COLUMN movimiento_inventario.id_pedido      IS 'Pedido que originó el movimiento (salida por venta o entrada por cancelación). NULL en movimientos manuales.';
COMMENT ON COLUMN movimiento_inventario.tipo           IS 'entrada (suma), salida (resta) o ajuste (diferencia con signo).';
COMMENT ON COLUMN movimiento_inventario.cantidad       IS 'entrada/salida: unidades positivas. ajuste: diferencia con signo aplicada al stock (positiva suma, negativa resta), nunca cero.';
COMMENT ON COLUMN movimiento_inventario.stock_anterior IS 'Stock de la variante inmediatamente antes del movimiento.';
COMMENT ON COLUMN movimiento_inventario.stock_nuevo    IS 'Stock resultante. Debe ser stock_anterior +/- cantidad según el tipo, y nunca negativo.';
COMMENT ON COLUMN movimiento_inventario.fecha          IS 'Instante del movimiento.';
COMMENT ON COLUMN movimiento_inventario.motivo         IS 'Justificación del movimiento (compra a proveedor, venta pedido N, conteo físico, etc.).';
COMMENT ON COLUMN movimiento_inventario.activo         IS 'Borrado lógico requerido por la asignatura. Desactivar un movimiento NO modifica el stock ni lo anula: la trazabilidad se calcula con todos los movimientos. Usar solo para ocultar registros en vistas administrativas.';


-- =============================================================================
-- Índices
-- (Los PRIMARY KEY y UNIQUE ya crean sus propios índices; no se duplican.)
-- =============================================================================

-- direccion: listar direcciones de un usuario (RF-11).
CREATE INDEX ix_direccion_id_usuario ON direccion (id_usuario);
-- direccion: como máximo una dirección principal activa por usuario.
CREATE UNIQUE INDEX ux_direccion_principal_activa
    ON direccion (id_usuario) WHERE principal AND activo;

-- producto: filtrar por categoría (RF-04) y validar la FK.
CREATE INDEX ix_producto_id_categoria ON producto (id_categoria);
-- producto: búsqueda por nombre sin distinguir mayúsculas, por prefijo
-- (lower(nombre) LIKE lower(:texto) || '%'). La búsqueda por referencia exacta
-- usa el índice de uq_producto_referencia.
CREATE INDEX ix_producto_nombre_lower ON producto (lower(nombre) text_pattern_ops);

-- variante_producto: las consultas por producto usan uq_variante_producto_combinacion
-- (columna inicial id_producto). Índice parcial para stock bajo (RF-34):
CREATE INDEX ix_variante_producto_stock_bajo
    ON variante_producto (id_producto) WHERE activo AND stock < stock_minimo;

-- carrito: historial de carritos por usuario y validación de la FK.
CREATE INDEX ix_carrito_id_usuario ON carrito (id_usuario);
-- carrito: como máximo un carrito abierto y activo por usuario.
CREATE UNIQUE INDEX ux_carrito_abierto_por_usuario
    ON carrito (id_usuario) WHERE activo AND estado = 'abierto';

-- detalle_carrito: una línea activa por variante en cada carrito; también
-- sirve para listar las líneas activas de un carrito.
CREATE UNIQUE INDEX ux_detalle_carrito_linea_activa
    ON detalle_carrito (id_carrito, id_variante) WHERE activo;

-- pedido: historial del cliente (RF-20), ordenado por fecha.
CREATE INDEX ix_pedido_id_usuario_fecha ON pedido (id_usuario, fecha DESC);
-- pedido: bandeja del empleado por estado (RF-32).
CREATE INDEX ix_pedido_estado_fecha ON pedido (estado, fecha DESC);
-- pedido: resumen por rango de fechas (RF-35).
CREATE INDEX ix_pedido_fecha ON pedido (fecha);

-- detalle_pedido: las consultas por pedido usan uq_detalle_pedido_pedido_variante.

-- movimiento_inventario: kardex por variante, por usuario y por fecha.
CREATE INDEX ix_movimiento_inventario_variante_fecha ON movimiento_inventario (id_variante, fecha DESC);
CREATE INDEX ix_movimiento_inventario_usuario_fecha  ON movimiento_inventario (id_usuario, fecha DESC);
CREATE INDEX ix_movimiento_inventario_fecha          ON movimiento_inventario (fecha);
-- Las consultas por pedido usan uq_movimiento_inventario_pedido_variante_tipo.


-- =============================================================================
-- Permisos
-- PostgreSQL no concede privilegios sobre tablas nuevas a PUBLIC; se revocan
-- explícitamente para dejarlo documentado. No se crean roles adicionales
-- (rol de mínimo privilegio para Flask: pendiente, ver README, decisión O6).
-- =============================================================================
REVOKE ALL ON TABLE
    usuario, direccion, categoria, producto, variante_producto,
    carrito, detalle_carrito, pedido, detalle_pedido, movimiento_inventario
FROM PUBLIC;

COMMIT;
