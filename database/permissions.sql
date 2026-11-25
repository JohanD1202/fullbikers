-- =============================================================================
-- FullBikers - Rol técnico de mínimo privilegio para la API Flask
-- -----------------------------------------------------------------------------
-- Estado        : verificado el 2026-11-25 en un clúster PostgreSQL 18.4 local
--                 temporal (ver database/README.md §18). Pendiente de
--                 ejecutar en Neon.
-- Requiere      : schema.sql ya aplicado en la rama de destino.
-- Ejecutar como : fullbikers_owner (propietario de las tablas), desde el
--                 SQL Editor de Neon, UNA VEZ POR RAMA (development y, cuando
--                 se despliegue, production). Cada rama con su propia
--                 contraseña.
-- No contiene contraseñas: se asignan después con ALTER ROLE (paso 2), escrito
-- directamente en el SQL Editor y nunca guardado en el repositorio.
--
-- Roles técnicos vs. roles funcionales
--   * Roles técnicos de PostgreSQL: fullbikers_owner (propietario, solo para
--     migraciones) y fullbikers_app (este script; lo usa la API).
--   * Roles funcionales de FullBikers: cliente, empleado y administrador. Son
--     VALORES de la columna usuario.rol y los aplica Flask en cada endpoint.
--     NO son roles de PostgreSQL: un administrador de la tienda nunca recibe
--     privilegios de base de datos; toda petición, de cualquier rol, llega a
--     PostgreSQL como fullbikers_app.
--
-- Por qué se crea por SQL y no desde la consola de Neon
--   Los roles creados desde la consola, la CLI o la API de Neon se vuelven
--   miembros de neon_superuser (puede crear roles y bases, y leer y escribir
--   todas las tablas). Un rol creado con CREATE ROLE no lo es.
--
-- Privilegios concedidos (y por qué)
--   * CONNECT a la base y USAGE sobre el esquema public.
--   * SELECT, INSERT, UPDATE en las tablas de operación normal.
--   * detalle_pedido y movimiento_inventario son históricos inmutables: SELECT
--     e INSERT, y UPDATE solo sobre la columna "activo" (borrado lógico exigido
--     por la asignatura; ver database/README.md §9).
--   * Sin DELETE ni TRUNCATE (borrado lógico), sin REFERENCES ni TRIGGER, sin
--     CREATE en la base ni en el esquema, sin propiedad de objetos.
--
-- Secuencias de identidad
--   Todas las PK son GENERATED ALWAYS AS IDENTITY. PostgreSQL obtiene el valor
--   de la secuencia interna sin comprobar privilegios sobre ella durante el
--   INSERT, por lo que NO se concede USAGE sobre secuencias. La API tampoco
--   llama a nextval()/currval(): obtiene los identificadores con RETURNING.
--
-- Privilegios heredados de PUBLIC (no se modifican para no afectar a otros roles)
--   * Base de datos: CONNECT y TEMPORARY (tablas temporales de la propia
--     sesión; no permiten leer ni modificar datos de la aplicación).
--   * Esquema public: USAGE. Desde PostgreSQL 15, PUBLIC no tiene CREATE.
--   * Tablas: schema.sql ya revocó todo a PUBLIC.
--   La sección de verificación muestra los privilegios efectivos resultantes.
--
-- ALTER DEFAULT PRIVILEGES: NO se usa
--   Concedería permisos automáticamente sobre cualquier tabla futura creada
--   por fullbikers_owner, sin revisión. Cada migración futura
--   (database/migrations/V00N__*.sql) incluirá sus propios GRANT explícitos y
--   revisados.
--
-- Endpoint de conexión: DIRECTO (host sin "-pooler")
--   La API ya mantiene su propio pool pequeño (Psycopg, máx. 5 por proceso).
--   Usar además el pooler de Neon (PgBouncer en modo transacción) añadiría una
--   segunda capa de pool sin beneficio para este tamaño de proyecto. Si en el
--   futuro hubiera muchos procesos o conexiones, se puede cambiar al endpoint
--   pooled sin modificar el código.
-- =============================================================================

BEGIN;

SET LOCAL search_path TO public;

-- -----------------------------------------------------------------------------
-- 1. Rol de conexión, sin atributos administrativos y sin contraseña.
--    Sin contraseña no puede iniciar sesión hasta completar el paso 2.
--    CONNECTION LIMIT acota el daño de un pool mal configurado.
-- -----------------------------------------------------------------------------
CREATE ROLE fullbikers_app WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS
    CONNECTION LIMIT 30;

COMMENT ON ROLE fullbikers_app IS
    'Rol técnico de la API Flask de FullBikers (mínimo privilegio). Sin DELETE, TRUNCATE ni DDL. Los roles cliente/empleado/administrador viven en usuario.rol.';

-- -----------------------------------------------------------------------------
-- 2. Acceso a la base y al esquema.
-- -----------------------------------------------------------------------------
GRANT CONNECT ON DATABASE fullbikers TO fullbikers_app;
GRANT USAGE ON SCHEMA public TO fullbikers_app;

-- -----------------------------------------------------------------------------
-- 3. Tablas de operación normal: lectura, alta y modificación.
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON TABLE
    usuario,
    direccion,
    categoria,
    producto,
    variante_producto,
    carrito,
    detalle_carrito,
    pedido
TO fullbikers_app;

-- -----------------------------------------------------------------------------
-- 4. Históricos inmutables: lectura, alta y solo borrado lógico.
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT ON TABLE detalle_pedido, movimiento_inventario TO fullbikers_app;
GRANT UPDATE (activo) ON TABLE detalle_pedido        TO fullbikers_app;
GRANT UPDATE (activo) ON TABLE movimiento_inventario TO fullbikers_app;

COMMIT;


-- =============================================================================
-- PASO 2 (manual, fuera de este archivo): asignar la contraseña.
-- Escribirlo directamente en el SQL Editor de la rama correspondiente, con una
-- contraseña generada (>= 24 caracteres aleatorios; Neon exige contraseñas
-- robustas). No guardar la contraseña en el repositorio ni en el historial
-- del chat del equipo.
--
--   ALTER ROLE fullbikers_app WITH PASSWORD '<contraseña generada>';
--
-- Generarla en la terminal, por ejemplo:
--   python -c "import secrets; print(secrets.token_urlsafe(32))"
-- =============================================================================


-- =============================================================================
-- VERIFICACIÓN (solo lectura). Ejecutar después del paso 2.
-- =============================================================================
BEGIN TRANSACTION READ ONLY;

-- V1. Atributos del rol. Esperado: rolcanlogin = true, rolconnlimit = 30 y
--     todos los demás atributos false. (pg_roles oculta la contraseña; que
--     quedó asignada se comprueba conectándose con la cadena del rol.)
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication,
       rolbypassrls, rolcanlogin, rolconnlimit
FROM pg_roles
WHERE rolname = 'fullbikers_app';

-- V2. Pertenencia a otros roles (incluido neon_superuser). Esperado: 0 filas.
SELECT r.rolname AS es_miembro_de
FROM pg_auth_members m
JOIN pg_roles r ON r.oid = m.roleid
JOIN pg_roles u ON u.oid = m.member
WHERE u.rolname = 'fullbikers_app';

-- V3. Privilegios efectivos por tabla (incluye los heredados de PUBLIC).
--     Esperado: SELECT/INSERT true; DELETE/TRUNCATE/REFERENCES/TRIGGER false;
--     UPDATE de tabla completa true salvo en detalle_pedido y
--     movimiento_inventario (false: solo la columna activo, ver V4).
SELECT t.tabla,
       has_table_privilege('fullbikers_app', t.tabla, 'SELECT')     AS select,
       has_table_privilege('fullbikers_app', t.tabla, 'INSERT')     AS insert,
       has_table_privilege('fullbikers_app', t.tabla, 'UPDATE')     AS update_tabla,
       has_table_privilege('fullbikers_app', t.tabla, 'DELETE')     AS delete,
       has_table_privilege('fullbikers_app', t.tabla, 'TRUNCATE')   AS truncate,
       has_table_privilege('fullbikers_app', t.tabla, 'REFERENCES') AS references,
       has_table_privilege('fullbikers_app', t.tabla, 'TRIGGER')    AS trigger
FROM (VALUES ('usuario'), ('direccion'), ('categoria'), ('producto'),
             ('variante_producto'), ('carrito'), ('detalle_carrito'),
             ('pedido'), ('detalle_pedido'), ('movimiento_inventario')) AS t(tabla)
ORDER BY t.tabla;

-- V4. UPDATE por columna en los históricos. Esperado: activo = true; las demás
--     columnas = false.
SELECT c.table_name AS tabla, c.column_name AS columna,
       has_column_privilege('fullbikers_app', c.table_schema || '.' || c.table_name,
                            c.column_name, 'UPDATE') AS puede_actualizar
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name IN ('detalle_pedido', 'movimiento_inventario')
ORDER BY c.table_name, c.ordinal_position;

-- V5. Privilegios sobre la base y el esquema. Esperado: connect = true,
--     create_en_base = false, usage_esquema = true, create_en_esquema = false.
--     temporary puede ser true (heredado de PUBLIC; ver encabezado).
SELECT has_database_privilege('fullbikers_app', current_database(), 'CONNECT')   AS connect,
       has_database_privilege('fullbikers_app', current_database(), 'CREATE')    AS create_en_base,
       has_database_privilege('fullbikers_app', current_database(), 'TEMPORARY') AS temporary,
       has_schema_privilege('fullbikers_app', 'public', 'USAGE')                 AS usage_esquema,
       has_schema_privilege('fullbikers_app', 'public', 'CREATE')                AS create_en_esquema;

-- V6. Objetos propiedad del rol. Esperado: 0 filas.
SELECT c.relname AS objeto, c.relkind AS tipo
FROM pg_class c
JOIN pg_roles r ON r.oid = c.relowner
WHERE r.rolname = 'fullbikers_app';

-- V7. Privilegios sobre las secuencias de identidad. Esperado: false (no se
--     necesitan; ver encabezado).
SELECT s.sequencename AS secuencia,
       has_sequence_privilege('fullbikers_app', s.schemaname || '.' || s.sequencename, 'USAGE') AS usage
FROM pg_sequences s
WHERE s.schemaname = 'public'
ORDER BY s.sequencename;

ROLLBACK;
