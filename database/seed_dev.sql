-- =============================================================================
-- FullBikers - Datos ficticios para DESARROLLO (catálogo)
-- -----------------------------------------------------------------------------
-- SOLO para la rama "development" de Neon. NUNCA ejecutar en production.
-- Estado        : verificado el 2026-11-25 en un clúster PostgreSQL 18.4 local
--                 temporal (dos ejecuciones, sin duplicados). Pendiente de
--                 ejecutar en la rama development de Neon.
-- Requiere      : schema.sql aplicado.
-- Ejecutar como : fullbikers_owner (SQL Editor de Neon, rama development).
--
-- Contenido     : categorías, productos y variantes. Sin usuarios, carritos,
--                 pedidos ni movimientos. Los usuarios de prueba se crean con
--                 el backend (hash Werkzeug), nunca con SQL:
--                   flask --app app crear-usuarios-prueba   (solo development)
-- Datos         : marcas, nombres y referencias inventados. Sin datos
--                 personales. Imágenes en NULL (el frontend muestra una
--                 imagen genérica).
-- Repetible     : usa ON CONFLICT DO NOTHING; volver a ejecutarlo no duplica
--                 filas ni modifica las existentes. No borra nada.
-- Stock inicial : se carga directamente en variante_producto.stock, sin
--                 movimiento_inventario, porque todo movimiento exige un
--                 usuario responsable y todavía no existen usuarios. La
--                 consulta 16 de verification.sql no lo reporta (solo compara
--                 variantes que ya tienen movimientos).
--
-- Casos de prueba incluidos (ver la consulta de resumen al final):
--   * 11 productos visibles en el catálogo (producto activo, categoría activa y
--     al menos una variante activa).
--   * Productos con stock, productos visibles sin stock (CAS-JET-003,
--     ACC-CAN-002) y variantes sin stock dentro de productos con stock.
--   * Variante inactiva con stock que NO debe sumar disponibilidad
--     (CAS-ABA-002-XL-BLA).
--   * Producto inactivo (CHA-CUE-002): no visible.
--   * Producto activo cuyas variantes están todas inactivas (ACC-LUZ-005):
--     no visible.
--   * Producto activo en categoría inactiva "Repuestos" (REP-PAS-001):
--     no visible.
--   * Variante base (talla, color y compatibilidad NULL) y variantes por
--     compatibilidad.
--   * Varias variantes con stock por debajo de stock_minimo (RF-34).
--   * Búsqueda con texto que contiene "%" o "_": ningún nombre los incluye,
--     así que buscar "%" debe devolver 0 resultados.
-- =============================================================================

BEGIN;

SET LOCAL search_path TO public;

-- Salvaguarda: si ya existen pedidos, la base tiene operación real y el script
-- se detiene sin cambiar nada (protección parcial contra ejecutarlo en
-- production; la responsabilidad principal es elegir la rama correcta).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pedido) THEN
        RAISE EXCEPTION 'seed_dev.sql: la base ya tiene pedidos. Este script es solo para la rama development vacía.';
    END IF;
END
$$;


-- -----------------------------------------------------------------------------
-- 1. Categorías (5 activas, 1 inactiva)
-- -----------------------------------------------------------------------------
INSERT INTO categoria (nombre, descripcion, activo) VALUES
    ('Cascos',       'Cascos integrales, abatibles y abiertos.',                    TRUE),
    ('Guantes',      'Guantes para clima cálido y frío.',                           TRUE),
    ('Chaquetas',    'Chaquetas con protecciones para motociclista.',               TRUE),
    ('Impermeables', 'Trajes y prendas impermeables para lluvia.',                  TRUE),
    ('Accesorios',   'Accesorios y equipamiento para la motocicleta.',              TRUE),
    ('Repuestos',    'Categoría inactiva de prueba: sus productos no se muestran.', FALSE)
ON CONFLICT DO NOTHING;


-- -----------------------------------------------------------------------------
-- 2. Productos (14: 11 visibles y 3 no visibles por diferentes motivos)
-- -----------------------------------------------------------------------------
INSERT INTO producto (id_categoria, nombre, referencia, descripcion, marca, precio, imagen, activo)
SELECT c.id_categoria, v.nombre, v.referencia, v.descripcion, v.marca, v.precio, NULL, v.activo
FROM (VALUES
    ('Cascos',       'Casco integral Ruta X1',             'CAS-INT-001', 'Casco integral con visor antiempañante y certificación de prueba.', 'MotoAndes',   450000.00::numeric(14,2), TRUE),
    ('Cascos',       'Casco abatible Urbano Pro',          'CAS-ABA-002', 'Casco abatible con gafa solar interna.',                           'RutaSegura',  380000.00::numeric(14,2), TRUE),
    ('Cascos',       'Casco jet Clásico',                  'CAS-JET-003', 'Casco abierto de estilo clásico. Sin existencias.',                'MotoAndes',   210000.00::numeric(14,2), TRUE),
    ('Guantes',      'Guantes de verano Ventila',          'GUA-VER-001', 'Guantes en malla transpirable con protección en nudillos.',        'RutaSegura',   85000.00::numeric(14,2), TRUE),
    ('Guantes',      'Guantes impermeables Invierno',      'GUA-INV-002', 'Guantes con membrana impermeable y forro térmico.',                'Cordillera',  120000.00::numeric(14,2), TRUE),
    ('Chaquetas',    'Chaqueta textil Travesía',           'CHA-TEX-001', 'Chaqueta textil con protecciones en hombros, codos y espalda.',    'Cordillera',  520000.00::numeric(14,2), TRUE),
    ('Chaquetas',    'Chaqueta de cuero Clásica',          'CHA-CUE-002', 'Producto inactivo de prueba: no debe aparecer en el catálogo.',    'MotoAndes',   690000.00::numeric(14,2), FALSE),
    ('Impermeables', 'Impermeable dos piezas Aguacero',    'IMP-2PZ-001', 'Chaqueta y pantalón impermeables con reflectivos.',                'RutaSegura',   95000.00::numeric(14,2), TRUE),
    ('Accesorios',   'Soporte de celular para manubrio',   'ACC-SOP-001', 'Soporte ajustable en aluminio. Producto sin variantes (variante base).', 'Cordillera', 65000.00::numeric(14,2), TRUE),
    ('Accesorios',   'Candado de disco con alarma',        'ACC-CAN-002', 'Candado de disco con alarma de 110 dB. Sin existencias.',          'MotoAndes',   110000.00::numeric(14,2), TRUE),
    ('Accesorios',   'Maleta trasera 30 L',                'ACC-MAL-003', 'Maleta rígida para parrilla trasera.',                             'RutaSegura',  230000.00::numeric(14,2), TRUE),
    ('Accesorios',   'Defensas laterales',                 'ACC-DEF-004', 'Defensas en acero según el tipo de motocicleta.',                  'Cordillera',  280000.00::numeric(14,2), TRUE),
    ('Accesorios',   'Exploradoras LED',                   'ACC-LUZ-005', 'Producto activo con todas sus variantes inactivas: no visible.',   'MotoAndes',   175000.00::numeric(14,2), TRUE),
    ('Repuestos',    'Pastillas de freno delanteras',      'REP-PAS-001', 'Producto activo en categoría inactiva: no visible.',               'Cordillera',   45000.00::numeric(14,2), TRUE)
) AS v(categoria, nombre, referencia, descripcion, marca, precio, activo)
JOIN categoria c ON lower(c.nombre) = lower(v.categoria)
ON CONFLICT DO NOTHING;


-- -----------------------------------------------------------------------------
-- 3. Variantes (stock_minimo predeterminado: 5)
-- -----------------------------------------------------------------------------
INSERT INTO variante_producto (id_producto, talla, color, compatibilidad, sku, stock, stock_minimo, activo)
SELECT p.id_producto, v.talla, v.color, v.compatibilidad, v.sku, v.stock, v.stock_minimo, v.activo
FROM (VALUES
    -- Casco integral: una talla sin stock.
    ('CAS-INT-001', 'S'::varchar,  'Negro mate'::varchar, NULL::varchar,             'CAS-INT-001-S-NEG',  5, 5, TRUE),
    ('CAS-INT-001', 'M',  'Negro mate', NULL,                       'CAS-INT-001-M-NEG',  8, 5, TRUE),
    ('CAS-INT-001', 'L',  'Negro mate', NULL,                       'CAS-INT-001-L-NEG',  0, 5, TRUE),
    -- Casco abatible: la variante XL está inactiva y NO debe sumar al stock visible (5).
    ('CAS-ABA-002', 'M',  'Blanco',     NULL,                       'CAS-ABA-002-M-BLA',  3, 5, TRUE),
    ('CAS-ABA-002', 'L',  'Blanco',     NULL,                       'CAS-ABA-002-L-BLA',  2, 5, TRUE),
    ('CAS-ABA-002', 'XL', 'Blanco',     NULL,                       'CAS-ABA-002-XL-BLA', 4, 5, FALSE),
    -- Casco jet: visible pero sin stock.
    ('CAS-JET-003', 'M',  'Rojo',       NULL,                       'CAS-JET-003-M-ROJ',  0, 5, TRUE),
    ('CAS-JET-003', 'L',  'Rojo',       NULL,                       'CAS-JET-003-L-ROJ',  0, 5, TRUE),
    -- Guantes de verano: la talla L está por debajo del mínimo.
    ('GUA-VER-001', 'S',  'Negro',      NULL,                       'GUA-VER-001-S-NEG', 10, 5, TRUE),
    ('GUA-VER-001', 'M',  'Negro',      NULL,                       'GUA-VER-001-M-NEG', 12, 5, TRUE),
    ('GUA-VER-001', 'L',  'Negro',      NULL,                       'GUA-VER-001-L-NEG',  3, 5, TRUE),
    -- Guantes de invierno.
    ('GUA-INV-002', 'M',  'Gris',       NULL,                       'GUA-INV-002-M-GRI',  4, 5, TRUE),
    ('GUA-INV-002', 'L',  'Gris',       NULL,                       'GUA-INV-002-L-GRI',  1, 5, TRUE),
    -- Chaqueta textil: dos colores.
    ('CHA-TEX-001', 'M',  'Negro',      NULL,                       'CHA-TEX-001-M-NEG',  3, 3, TRUE),
    ('CHA-TEX-001', 'L',  'Negro',      NULL,                       'CHA-TEX-001-L-NEG',  2, 3, TRUE),
    ('CHA-TEX-001', 'L',  'Gris',       NULL,                       'CHA-TEX-001-L-GRI',  0, 3, TRUE),
    -- Chaqueta de cuero (producto inactivo).
    ('CHA-CUE-002', 'M',  'Café',       NULL,                       'CHA-CUE-002-M-CAF',  5, 5, TRUE),
    -- Impermeable.
    ('IMP-2PZ-001', 'M',  'Amarillo',   NULL,                       'IMP-2PZ-001-M-AMA',  7, 5, TRUE),
    ('IMP-2PZ-001', 'L',  'Amarillo',   NULL,                       'IMP-2PZ-001-L-AMA',  9, 5, TRUE),
    ('IMP-2PZ-001', 'XL', 'Amarillo',   NULL,                       'IMP-2PZ-001-XL-AMA', 2, 5, TRUE),
    -- Variantes base (sin talla, color ni compatibilidad).
    ('ACC-SOP-001', NULL, NULL,         NULL,                       'ACC-SOP-001',       20, 5, TRUE),
    ('ACC-CAN-002', NULL, NULL,         NULL,                       'ACC-CAN-002',        0, 5, TRUE),
    -- Variantes por compatibilidad.
    ('ACC-MAL-003', NULL, 'Negro',      'Universal para parrilla',  'ACC-MAL-003-UNI',    6, 2, TRUE),
    ('ACC-DEF-004', NULL, NULL,         'Motocicleta urbana 150 cc',  'ACC-DEF-004-URB150', 2, 2, TRUE),
    ('ACC-DEF-004', NULL, NULL,         'Motocicleta deportiva 250 cc', 'ACC-DEF-004-DEP250', 0, 2, TRUE),
    -- Exploradoras: todas las variantes inactivas.
    ('ACC-LUZ-005', NULL, 'Blanco',     NULL,                       'ACC-LUZ-005-BLA',    8, 5, FALSE),
    ('ACC-LUZ-005', NULL, 'Ámbar',      NULL,                       'ACC-LUZ-005-AMB',    6, 5, FALSE),
    -- Pastillas de freno (categoría inactiva).
    ('REP-PAS-001', NULL, NULL,         'Motocicleta urbana 150 cc',  'REP-PAS-001-URB150', 15, 5, TRUE)
) AS v(referencia, talla, color, compatibilidad, sku, stock, stock_minimo, activo)
JOIN producto p ON p.referencia = v.referencia
ON CONFLICT DO NOTHING;

COMMIT;


-- =============================================================================
-- Resumen (solo lectura). Resultado esperado tras la primera ejecución:
--   visibles = 11; con_stock = 9; sin_stock = 2 (CAS-JET-003, ACC-CAN-002);
--   CAS-ABA-002 con stock visible 5 (la variante XL inactiva no suma).
-- =============================================================================
SELECT p.referencia,
       p.nombre,
       c.nombre                        AS categoria,
       p.precio,
       COUNT(vp.id_variante)           AS variantes_activas,
       COALESCE(SUM(vp.stock), 0)      AS stock_visible,
       (p.activo AND c.activo AND COUNT(vp.id_variante) > 0) AS visible_en_catalogo
FROM producto p
JOIN categoria c               ON c.id_categoria = p.id_categoria
LEFT JOIN variante_producto vp ON vp.id_producto = p.id_producto AND vp.activo
GROUP BY p.id_producto, c.nombre, c.activo
ORDER BY visible_en_catalogo DESC, p.referencia;
