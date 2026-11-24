-- =============================================================================
-- FullBikers - Verificación del esquema (solo lectura)
-- -----------------------------------------------------------------------------
-- Ejecutar DESPUÉS de schema.sql. Todas las consultas son de solo lectura y se
-- ejecutan dentro de una transacción READ ONLY que termina con ROLLBACK: este
-- script no puede modificar datos ni estructura.
-- No inserta datos de prueba.
-- =============================================================================

BEGIN TRANSACTION READ ONLY;

-- 1. Base de datos, usuario y versión del servidor ---------------------------
SELECT current_database()                 AS base_de_datos,
       current_user                       AS usuario_actual,
       current_setting('server_version')  AS version_postgresql,
       current_setting('TimeZone')        AS zona_horaria_sesion;

-- 2. Existencia de las diez tablas (esperado: 10 filas con existe = true) -----
SELECT t.tabla,
       to_regclass('public.' || t.tabla) IS NOT NULL AS existe
FROM (VALUES ('usuario'), ('direccion'), ('categoria'), ('producto'),
             ('variante_producto'), ('carrito'), ('detalle_carrito'),
             ('pedido'), ('detalle_pedido'), ('movimiento_inventario')) AS t(tabla)
ORDER BY t.tabla;

-- 3. Cantidad de atributos por tabla (esperado: >= 5 en todas) ----------------
SELECT c.table_name             AS tabla,
       count(*)                 AS atributos,
       count(*) >= 5            AS cumple_minimo
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'
GROUP BY c.table_name
ORDER BY c.table_name;

-- 4. Columnas, tipos, nulabilidad y valores predeterminados -------------------
SELECT table_name  AS tabla,
       ordinal_position AS pos,
       column_name AS columna,
       CASE WHEN data_type = 'character varying'
            THEN 'varchar(' || character_maximum_length || ')'
            WHEN data_type = 'numeric'
            THEN 'numeric(' || numeric_precision || ',' || numeric_scale || ')'
            ELSE data_type END AS tipo,
       is_nullable  AS acepta_null,
       column_default AS valor_predeterminado,
       is_identity  AS identidad,
       is_generated AS generada
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 5. Claves primarias (esperado: 10, todas IDENTITY) --------------------------
SELECT con.conrelid::regclass AS tabla,
       con.conname            AS restriccion,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_namespace n ON n.oid = con.connamespace
WHERE n.nspname = 'public' AND con.contype = 'p'
ORDER BY con.conrelid::regclass::text;

-- 6. Claves foráneas y su comportamiento (esperado: RESTRICT en todas) --------
SELECT con.conrelid::regclass  AS tabla,
       con.conname             AS restriccion,
       con.confrelid::regclass AS tabla_referenciada,
       pg_get_constraintdef(con.oid) AS definicion,
       CASE con.confdeltype WHEN 'r' THEN 'RESTRICT' WHEN 'a' THEN 'NO ACTION'
            WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' END AS on_delete,
       CASE con.confupdtype WHEN 'r' THEN 'RESTRICT' WHEN 'a' THEN 'NO ACTION'
            WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' END AS on_update
FROM pg_constraint con
JOIN pg_namespace n ON n.oid = con.connamespace
WHERE n.nspname = 'public' AND con.contype = 'f'
ORDER BY con.conrelid::regclass::text, con.conname;

-- 7. Restricciones UNIQUE ------------------------------------------------------
SELECT con.conrelid::regclass AS tabla,
       con.conname            AS restriccion,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_namespace n ON n.oid = con.connamespace
WHERE n.nspname = 'public' AND con.contype = 'u'
ORDER BY con.conrelid::regclass::text, con.conname;

-- 7b. Índices únicos que no provienen de una restricción (por expresión o parciales)
SELECT i.indrelid::regclass AS tabla,
       c.relname            AS indice,
       pg_get_indexdef(i.indexrelid) AS definicion
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND i.indisunique
  AND NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conindid = i.indexrelid)
ORDER BY i.indrelid::regclass::text, c.relname;

-- 8. Restricciones CHECK -------------------------------------------------------
SELECT con.conrelid::regclass AS tabla,
       con.conname            AS restriccion,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_namespace n ON n.oid = con.connamespace
WHERE n.nspname = 'public' AND con.contype = 'c'
ORDER BY con.conrelid::regclass::text, con.conname;

-- 9. Atributo "activo" en todas las tablas ------------------------------------
--    Esperado: 10 filas, tipo boolean, NOT NULL y predeterminado true.
SELECT t.table_name AS tabla,
       c.column_name IS NOT NULL                     AS tiene_activo,
       c.data_type                                   AS tipo,
       c.is_nullable = 'NO'                          AS not_null,
       c.column_default                              AS valor_predeterminado,
       (c.data_type = 'boolean' AND c.is_nullable = 'NO'
        AND lower(c.column_default) = 'true')        AS cumple
FROM information_schema.tables t
LEFT JOIN information_schema.columns c
       ON c.table_schema = t.table_schema
      AND c.table_name   = t.table_name
      AND c.column_name  = 'activo'
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name;

-- 10. Índices creados ----------------------------------------------------------
SELECT tablename AS tabla,
       indexname AS indice,
       indexdef  AS definicion
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 11. Triggers definidos por el usuario (esperado: 0 filas) -------------------
SELECT tgrelid::regclass AS tabla, tgname AS trigger
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND NOT t.tgisinternal;

-- 12. Privilegios concedidos a PUBLIC sobre las tablas (esperado: 0 filas) ----
SELECT table_name AS tabla, privilege_type AS privilegio
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee = 'PUBLIC';

-- 13. Comentarios de tablas (documentación embebida) --------------------------
SELECT c.relname AS tabla, obj_description(c.oid, 'pg_class') AS comentario
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;

-- =============================================================================
-- Consultas de integridad de datos (útiles cuando ya existan datos).
-- En una base recién creada todas deben devolver 0 filas.
-- =============================================================================

-- 14. Productos sin ninguna variante (todo producto debe tener al menos una).
SELECT p.id_producto, p.referencia, p.nombre
FROM producto p
WHERE NOT EXISTS (SELECT 1 FROM variante_producto v WHERE v.id_producto = p.id_producto);

-- 15. Pedidos cuyo subtotal no coincide con la suma de sus líneas.
SELECT p.id_pedido, p.subtotal, COALESCE(sum(d.subtotal), 0) AS suma_lineas
FROM pedido p
LEFT JOIN detalle_pedido d ON d.id_pedido = p.id_pedido
GROUP BY p.id_pedido, p.subtotal
HAVING p.subtotal <> COALESCE(sum(d.subtotal), 0);

-- 16. Variantes cuyo stock actual no coincide con el último movimiento.
SELECT v.id_variante, v.sku, v.stock, ult.stock_nuevo AS stock_segun_ultimo_movimiento
FROM variante_producto v
JOIN LATERAL (
    SELECT m.stock_nuevo
    FROM movimiento_inventario m
    WHERE m.id_variante = v.id_variante
    ORDER BY m.fecha DESC, m.id_movimiento DESC
    LIMIT 1
) ult ON TRUE
WHERE v.stock <> ult.stock_nuevo;

-- 17. Cortes en la cadena de movimientos (stock_anterior distinto del
--     stock_nuevo del movimiento previo de la misma variante).
SELECT id_variante, id_movimiento, stock_anterior, stock_nuevo_previo
FROM (
    SELECT m.id_variante, m.id_movimiento, m.stock_anterior,
           lag(m.stock_nuevo) OVER (PARTITION BY m.id_variante
                                    ORDER BY m.fecha, m.id_movimiento) AS stock_nuevo_previo
    FROM movimiento_inventario m
) x
WHERE stock_nuevo_previo IS NOT NULL AND stock_anterior <> stock_nuevo_previo;

-- 18. Pedidos no cancelados con líneas sin su movimiento de salida.
SELECT d.id_pedido, d.id_variante, d.cantidad
FROM detalle_pedido d
JOIN pedido p ON p.id_pedido = d.id_pedido
WHERE p.estado <> 'cancelado'
  AND NOT EXISTS (SELECT 1 FROM movimiento_inventario m
                  WHERE m.id_pedido = d.id_pedido AND m.id_variante = d.id_variante
                    AND m.tipo = 'salida' AND m.cantidad = d.cantidad);

-- 19. Pedidos cancelados con líneas sin su devolución (entrada) correspondiente.
SELECT d.id_pedido, d.id_variante, d.cantidad
FROM detalle_pedido d
JOIN pedido p ON p.id_pedido = d.id_pedido
WHERE p.estado = 'cancelado'
  AND EXISTS (SELECT 1 FROM movimiento_inventario m
              WHERE m.id_pedido = d.id_pedido AND m.id_variante = d.id_variante AND m.tipo = 'salida')
  AND NOT EXISTS (SELECT 1 FROM movimiento_inventario m
                  WHERE m.id_pedido = d.id_pedido AND m.id_variante = d.id_variante
                    AND m.tipo = 'entrada' AND m.cantidad = d.cantidad);

-- 20. Pedidos cuya copia de entrega difiere de la dirección referenciada
--     (informativo: es esperado si el cliente editó la dirección después).
SELECT p.id_pedido, p.id_direccion
FROM pedido p
JOIN direccion d ON d.id_direccion = p.id_direccion
WHERE (d.departamento, d.municipio, d.direccion)
      IS DISTINCT FROM (p.departamento_entrega, p.municipio_entrega, p.direccion_entrega);

ROLLBACK;
