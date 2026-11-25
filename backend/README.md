# FullBikers — Backend (API REST con Flask)

API REST de FullBikers: Flask + Psycopg 3 sobre PostgreSQL (Neon), con arquitectura MVC, patrón DAO y capa de servicios. La vista es la aplicación React del directorio `frontend/`.

Contratos de la API para el frontend: [`API.md`](API.md).

## 1. Estado actual

| Componente | Estado |
|---|---|
| Application Factory, configuración por entorno, errores JSON, logging, CORS | Implementado y probado |
| Pool de conexiones Psycopg 3 y transacciones compartidas entre DAO | Implementado; probado contra PostgreSQL 18 local. **Sin verificar contra Neon** |
| `GET /api/health`, `GET /api/health/db` | Implementados (públicos) |
| Autenticación: registro de clientes, login, logout, usuario actual (RF-06 a RF-09) | Implementado y probado (unitarias + integración) |
| Autorización por rol (`cliente`, `empleado`, `administrador`) y apoyo para propiedad de recursos | Implementado y probado |
| Catálogo (`/api/principal`, `/api/productos`, `/api/productos/{id}`) protegido | Implementado y probado (RF-01 a RF-05) |
| Comandos `crear-admin` y `crear-usuarios-prueba` | Implementados y probados |
| Perfil, direcciones, carrito, pedidos, administración | Pendientes |

## 2. Arquitectura

```
React (vista) ──HTTP/JSON──▶ controllers ──▶ services ──▶ dao ──SQL──▶ PostgreSQL
                                  │              │          │
                             validan         reglas de   SQL parametrizado,
                             parámetros y    negocio y   sin commit/rollback
                             responden       transacción
                                     models: entidades y serialización
              middleware: errores JSON, JWT y autorización por rol (decoradores)
```

| Capa | Responsabilidad | No hace |
|---|---|---|
| `controllers/` | Rutas (Blueprints), validación de parámetros, respuesta HTTP | SQL ni reglas de negocio |
| `services/` | Casos de uso; abren la conexión o la transacción y coordinan uno o varios DAO | HTTP |
| `dao/` | Consultas SQL parametrizadas; reciben la conexión como primer argumento | `commit`, `rollback`, abrir conexiones |
| `models/` | Entidades (`Producto`, `Categoria`, `Usuario`, ...) y su serialización (`to_dict`) | Acceso a datos |
| `middleware/` | Manejo centralizado de errores; autenticación JWT y autorización por rol | — |
| `config/` | Configuración por entorno, pool de conexiones, logging | — |
| `comandos.py` | Comandos de consola de Flask (administrador inicial, usuarios de prueba) | — |

Sin ORM: el acceso a PostgreSQL es SQL parametrizado con Psycopg 3.

### Transacciones

```python
from config import database

# Lecturas: una conexión del pool. Al salir se confirma (o revierte si hubo error).
with database.obtener_conexion() as conn:
    productos = ProductoDAO.listar_catalogo(conn)

# Operación de negocio con varias escrituras: UNA transacción para todos los DAO.
with database.transaccion() as conn:
    pedido = PedidoDAO.crear(conn, ...)
    InventarioDAO.registrar_salida(conn, ...)   # si falla, se revierte todo
```

### Estructura

```
backend/
├── app.py                      # create_app(): Application Factory
├── comandos.py                 # flask crear-admin, flask crear-usuarios-prueba
├── exceptions.py               # ApiError y excepciones de dominio (400/401/403/404/409/429)
├── config/
│   ├── settings.py             # DevelopmentConfig, TestingConfig, ProductionConfig (+ JWT 60 min)
│   ├── database.py             # Pool Psycopg 3, obtener_conexion(), transaccion()
│   └── logs.py                 # Logging con ocultamiento de credenciales y tokens
├── controllers/
│   ├── health_controller.py    # /api/health, /api/health/db
│   ├── auth_controller.py      # /api/auth/register, /login, /logout, /me
│   ├── catalogo_controller.py  # /api/principal, /api/productos (protegidos)
│   └── parametros.py           # Validación de parámetros de consulta
├── services/
│   ├── auth_service.py         # Registro de clientes e inicio de sesión
│   ├── usuario_service.py      # Validación y creación de usuarios; usuario activo
│   ├── limitador_intentos.py   # Intentos fallidos de login (en memoria)
│   └── catalogo_service.py
├── dao/{producto_dao.py, usuario_dao.py}
├── models/{producto.py, usuario.py, dinero.py}
├── middleware/
│   ├── error_handlers.py
│   └── auth.py                 # requiere_autenticacion, requiere_rol, exigir_propietario
├── tests/                      # pruebas unitarias (sin base de datos)
│   └── integracion/            # pruebas contra PostgreSQL local real
├── requirements.txt / requirements-dev.txt / pytest.ini
├── .env.example                # plantilla de variables (sin valores reales)
└── API.md                      # contratos REST
```

## 3. Versiones

| Componente | Versión |
|---|---|
| Python | **3.14.3** (local y Render) |
| Flask | 3.1.3 (Werkzeug 3.1.9: hash de contraseñas scrypt) |
| flask-cors | 6.0.5 |
| Flask-JWT-Extended | 4.7.4 (PyJWT 2.x) |
| psycopg[binary] | 3.3.9 |
| psycopg-pool | 3.3.3 |
| python-dotenv | 1.2.4 |
| gunicorn | 27.0.1 (solo Linux/Render; se omite en Windows) |
| pytest | 9.2.0 (desarrollo) |
| PostgreSQL | 18 (Neon 18.7; pruebas locales con 18.4) |

## 4. Instalación en Windows (PowerShell)

Requisitos: Python 3.14 (`py -0` debe listar `3.14`) y Git.

```powershell
cd "<ruta del repositorio>\backend"
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Si PowerShell bloquea `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y repetir.
En VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → `backend\.venv\Scripts\python.exe`.

## 5. Variables de entorno (`backend/.env`)

Se definen en `backend/.env` (excluido de Git) a partir de [`.env.example`](.env.example).

| Variable | Obligatoria | Uso |
|---|---|---|
| `APP_ENV` | No (`development`) | `development`, `testing` o `production` |
| `SECRET_KEY` | Sí en producción | Firma de Flask. ≥ 32 caracteres aleatorios |
| `JWT_SECRET_KEY` | Sí en producción | Firma de los JWT. ≥ 32 caracteres, distinta de `SECRET_KEY`. En desarrollo, si falta, se genera una al arrancar (los tokens dejan de valer al reiniciar Flask) |
| `DATABASE_URL` | Sí en producción | Conexión a Neon con el rol `fullbikers_app`, endpoint directo, `sslmode=require` |
| `CORS_ORIGINS` | Sí en producción | Orígenes del frontend separados por comas; `*` no se admite en producción |
| `DB_POOL_MIN_SIZE` / `DB_POOL_MAX_SIZE` | No (0 / 5) | Tamaño del pool por proceso |
| `DB_CONNECT_TIMEOUT` | No (10) | Segundos para conectar u obtener conexión del pool |
| `PORT` | No (5000) | Puerto de `python app.py` y de Gunicorn en Render |
| `LOG_LEVEL` | No (`INFO`) | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `TEST_DATABASE_URL` | Solo pruebas de integración | PostgreSQL **local** temporal (§7.2). No va en `.env` |

Ejemplo de `backend/.env` para desarrollo (los valores entre `<>` se reemplazan):

```dotenv
APP_ENV=development
SECRET_KEY=<generado 1>
JWT_SECRET_KEY=<generado 2, distinto>
DATABASE_URL=postgresql://fullbikers_app:<contraseña>@<host-directo>.neon.tech/fullbikers?sslmode=require&channel_binding=require
CORS_ORIGINS=http://localhost:5173
```

Generar cada secreto: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

`ProductionConfig` se niega a arrancar si faltan secretos, si son cortos o parecen de ejemplo, si `DATABASE_URL` no exige SSL o si CORS admite `*`. Los mensajes nombran la variable, nunca su valor.

Sin `DATABASE_URL`, la API arranca en desarrollo: `/api/health` responde 200 y los endpoints que usan la base responden 503.

## 6. Ejecución local

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
flask --app app run --debug          # http://127.0.0.1:5000
```

Alternativa: `python app.py` (escucha en `127.0.0.1:$PORT`; modo debug solo si `FLASK_DEBUG=1`).

Comprobación rápida (PowerShell; `curl.exe`, no el alias `curl`):

```powershell
curl.exe http://127.0.0.1:5000/api/health
curl.exe http://127.0.0.1:5000/api/health/db
```

Gunicorn no funciona en Windows; solo se usa en Render.

### 6.1 Probar registro, login y catálogo

```powershell
$api = "http://127.0.0.1:5000/api"

# Registro (siempre crea un cliente)
$registro = @{ nombre = "Ana"; apellido = "Pérez"; correo = "ana@ejemplo.com"; contrasena = "Segura2026" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$api/auth/register" -ContentType "application/json; charset=utf-8" -Body $registro

# Login: guarda el token
$login = @{ correo = "ana@ejemplo.com"; contrasena = "Segura2026" } | ConvertTo-Json
$sesion = Invoke-RestMethod -Method Post -Uri "$api/auth/login" -ContentType "application/json" -Body $login
$auth = @{ Authorization = "Bearer $($sesion.access_token)" }

Invoke-RestMethod -Uri "$api/auth/me" -Headers $auth
Invoke-RestMethod -Uri "$api/principal" -Headers $auth
Invoke-RestMethod -Uri "$api/productos?busqueda=casco&pagina=1&por_pagina=5" -Headers $auth
Invoke-RestMethod -Uri "$api/productos" -ErrorAction Continue      # sin token: 401
Invoke-WebRequest -Method Post -Uri "$api/auth/logout" -Headers $auth  # 204
```

## 7. Pruebas

Hay dos tipos de pruebas, claramente separadas:

| Tipo | Ubicación | Base de datos | Cuándo |
|---|---|---|---|
| **Unitarias** | `tests/*.py` | Ninguna (dobles en memoria). La configuración `testing` ignora `DATABASE_URL` | Siempre, antes de cada Pull Request |
| **Integración** | `tests/integracion/` (marcador `integracion`) | PostgreSQL **local y temporal** real, indicado en `TEST_DATABASE_URL` | Al cambiar SQL, DAO, permisos o autenticación |

### 7.1 Unitarias

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -m "not integracion"
```

Sin `TEST_DATABASE_URL`, `python -m pytest` ejecuta las unitarias y marca las de integración como omitidas (`skipped`).

### 7.2 Integración con PostgreSQL local temporal

Las pruebas solo aceptan servidores en `localhost` (se niegan a ejecutarse contra Neon) y crean usuarios que no pueden borrar, por lo que se usa un clúster desechable. Requiere PostgreSQL 18 instalado (solo sus binarios; no se usa el servicio de Windows ni sus bases).

```powershell
$bin  = "C:\Program Files\PostgreSQL\18\bin"
$tmp  = Join-Path $env:TEMP "fullbikers_pg"            # directorio temporal
$port = 55433                                          # puerto independiente
$pwSuper = python -c "import secrets; print(secrets.token_urlsafe(24))"
$pwOwner = python -c "import secrets; print(secrets.token_urlsafe(24))"
$pwApp   = python -c "import secrets; print(secrets.token_urlsafe(24))"

# 1. Crear e iniciar el clúster (solo localhost)
$pwSuper | Out-File -Encoding ascii "$env:TEMP\pw.txt"
& "$bin\initdb.exe" -D $tmp -U postgres --pwfile="$env:TEMP\pw.txt" -A scram-sha-256 -E UTF8 --locale-provider=builtin --builtin-locale=C.UTF-8 --locale=C
Remove-Item "$env:TEMP\pw.txt"
Start-Process "$bin\postgres.exe" -ArgumentList "-D `"$tmp`" -p $port -c listen_addresses=localhost" -WindowStyle Hidden

# 2. Réplica mínima de Neon: rol propietario y base fullbikers
$env:PGPASSWORD = $pwSuper
& "$bin\psql.exe" -h localhost -p $port -U postgres -c "CREATE ROLE fullbikers_owner LOGIN CREATEROLE PASSWORD '$pwOwner';" -c "CREATE DATABASE fullbikers OWNER fullbikers_owner;"

# 3. Scripts del repositorio, como propietario (desde la raíz del repositorio)
$env:PGPASSWORD = $pwOwner
$psql = { & "$bin\psql.exe" -h localhost -p $port -U fullbikers_owner -d fullbikers -v ON_ERROR_STOP=1 @args }
& $psql -f database\schema.sql
& $psql -f database\verification.sql
& $psql -f database\permissions.sql
& $psql -c "ALTER ROLE fullbikers_app WITH PASSWORD '$pwApp';"
& $psql -f database\seed_dev.sql

# 4. Pruebas de integración (como fullbikers_app)
cd backend
$env:TEST_DATABASE_URL = "postgresql://fullbikers_app:$pwApp@localhost:$port/fullbikers"
python -m pytest tests\integracion
Remove-Item Env:TEST_DATABASE_URL, Env:PGPASSWORD

# 5. Detener y eliminar el clúster
& "$bin\pg_ctl.exe" -D $tmp -m fast stop
Remove-Item -Recurse -Force $tmp
```

Las pruebas de integración verifican: permisos efectivos de `fullbikers_app` (sin `DELETE`, `TRUNCATE` ni DDL; privilegios heredados de `PUBLIC`), columnas de identidad, restricciones e integridad referencial, precisión de precios, consultas reales del catálogo (búsqueda, filtros, paginación, stock, exclusión de inactivos) y los flujos completos de registro, login, autorización, logout y comandos de consola.

Antes de abrir un Pull Request: pruebas unitarias en verde, la API arranca con `flask --app app run`, y el diff no incluye `.env`, `.venv` ni credenciales.

## 8. Autenticación y autorización

**Regla general:** todo el sistema exige iniciar sesión. Públicos solo: `POST /api/auth/register` (clientes), `POST /api/auth/login` y `/api/health*`.

### Roles funcionales vs. roles técnicos

| Rol funcional (columna `usuario.rol`) | Responsabilidades | RF de referencia |
|---|---|---|
| `cliente` | Registrarse; iniciar/cerrar sesión; catálogo, búsqueda, filtro y detalle; datos personales; direcciones; carrito; pedidos; historial y estado de sus pedidos | RF-01–RF-21 |
| `empleado` | Iniciar/cerrar sesión; **consultar el catálogo** (productos y variantes para verificar pedidos e inventario); consultar, verificar y confirmar pedidos y actualizar sus estados; inventario; alertas de stock bajo | RF-01–RF-05 (consulta), RF-08, RF-09, RF-29–RF-34 |
| `administrador` | Todo lo anterior; administrar usuarios, productos, categorías, variantes, precios e imágenes; reportes | Todos |

Los roles técnicos de PostgreSQL son otra cosa: la API se conecta siempre como `fullbikers_app` (sin DDL ni DELETE). Ser administrador de la tienda **no** otorga privilegios de base de datos.

### Decisiones aprobadas

1. **JWT de acceso de 60 minutos, sin refresh token** (Flask-JWT-Extended, HS256, `JWT_SECRET_KEY`). `sub` = `id_usuario` (texto). Se envía en `Authorization: Bearer <token>`. El frontend lo guarda en `sessionStorage`.
2. **La autorización no confía en el rol del token.** En cada petición protegida el middleware valida el JWT y lee el usuario de PostgreSQL: si no existe o `activo = false` → `401`; su rol actual decide el acceso → `403` si no corresponde. El administrador supera cualquier verificación de rol.
3. **Registro solo de clientes.** Lista blanca de campos; `rol`, `activo`, `id_usuario` u otro campo → `400 campo_no_permitido`. El backend fija `rol = 'cliente'`. Correo normalizado (`strip().lower()`); duplicado → `409 correo_ya_registrado` (también si dos registros simultáneos chocan con `uq_usuario_correo`).
4. **Contraseñas:** 8–128 caracteres, al menos una letra y un número; hash scrypt de Werkzeug. Nunca se registran en logs ni se devuelven.
5. **Login sin enumeración:** mismo `401 credenciales_invalidas` para correo inexistente, contraseña incorrecta o cuenta inactiva; si el correo no existe se verifica contra un hash ficticio para igualar tiempos.
6. **Intentos fallidos:** limitador en memoria por correo + IP: 5 fallos en 15 minutos → `429` con `Retry-After`; un login correcto reinicia el contador. Limitación conocida: es por proceso (cada worker de Gunicorn cuenta por separado) y se reinicia con el servicio; detrás del proxy de Render la IP vista es la del proxy, así que en la práctica el límite es por correo.
7. **Cierre de sesión:** `POST /api/auth/logout` exige token y responde `204`; el frontend elimina el token de `sessionStorage`. **No hay revocación en el servidor:** un token copiado sigue siendo válido hasta su expiración (máx. 60 min), salvo que el usuario sea desactivado. Limitación aceptada para el alcance académico; no se agregan tablas ni columnas de sesiones.
8. **Administrador inicial:** comando `flask --app app crear-admin` (§9.3). No existen contraseñas predeterminadas.

### Cómo proteger un endpoint nuevo

```python
from middleware.auth import requiere_autenticacion, requiere_rol, usuario_actual, exigir_propietario
from models.usuario import CLIENTE, EMPLEADO

@bp.get("/api/pedidos")
@requiere_rol(CLIENTE)                      # cliente (y administrador)
def listar_pedidos():
    id_usuario = usuario_actual().id_usuario  # NUNCA tomarlo del cuerpo ni de la URL
    ...

@bp.get("/api/inventario/stock-bajo")
@requiere_rol(EMPLEADO)                     # empleado (y administrador)
def stock_bajo(): ...

@bp.get("/api/direcciones/<int:id_direccion>")
@requiere_rol(CLIENTE)
def ver_direccion(id_direccion):
    direccion = direccion_service.obtener(id_direccion)
    exigir_propietario(direccion.id_usuario)  # ajeno -> 404 (el administrador sí accede)
    ...
```

`@requiere_autenticacion` admite cualquier rol activo. En listados, filtrar en SQL con `WHERE id_usuario = %s` usando `usuario_actual().id_usuario`.

## 9. Neon: desarrollo y producción

| Rama de Neon | Uso | Quién usa sus credenciales |
|---|---|---|
| `development` | Desarrollo local y pruebas del equipo | Todo el equipo (rol `fullbikers_app` de esa rama) |
| `production` | Solo la API desplegada en Render | Solo Render |

### 9.1 Configuración manual (responsable de la base de datos, una vez por rama)

En la consola de Neon → proyecto FullBikers → **SQL Editor**, base `fullbikers`, rol `fullbikers_owner`:

1. **Rama `development`:** si no existe, crearla desde `production` (Branches → *Create branch*). Hereda el esquema ya aplicado.
2. Pegar y ejecutar `database/permissions.sql` completo. Resultado: `COMMIT` y las consultas V1–V7 con los valores esperados (ver comentarios del archivo y `database/README.md` §18).
3. Generar una contraseña en la terminal local (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) y ejecutar **solo en el editor**, sin guardarla en archivos:
   `ALTER ROLE fullbikers_app WITH PASSWORD '<contraseña generada>';`
4. **Solo en `development`:** pegar y ejecutar `database/seed_dev.sql` (repetible; no ejecutar nunca en `production`).
5. En **Connection Details**: rama `development`, base `fullbikers`, rol `fullbikers_app`, **desactivar "Connection pooling"** (endpoint directo, host sin `-pooler`). Copiar la cadena; debe terminar en `?sslmode=require&channel_binding=require`.
6. Compartir esa `DATABASE_URL` con el equipo por un canal privado (nunca en el repositorio, issues ni chats públicos).
7. Repetir los pasos 2, 3 y 5 en `production` (sin el paso 4) solo cuando se configure Render, con **otra** contraseña.

### 9.2 Comprobar la conexión

Con la `DATABASE_URL` en `backend/.env`: `flask --app app run` y abrir `http://127.0.0.1:5000/api/health/db` → `{"estado": "OK", "base_de_datos": "disponible"}`.

### 9.3 Usuarios de los tres roles

```powershell
cd backend; .\.venv\Scripts\Activate.ps1

# Administrador inicial (development y, más adelante, production).
# Pide nombre, apellido, correo, teléfono opcional y la contraseña de forma oculta (dos veces).
flask --app app crear-admin

# Solo development (APP_ENV=development): cliente, empleado y administrador de prueba.
# Correos: cliente@fullbikers.test, empleado@fullbikers.test, admin@fullbikers.test.
# Pide una contraseña (oculta) común a los tres. Si un correo ya existe, se omite.
flask --app app crear-usuarios-prueba
```

Ninguno de los dos comandos modifica usuarios existentes ni convierte a alguien en administrador. Los clientes reales se registran con `POST /api/auth/register`. Hasta que exista la administración de usuarios, un empleado real se crea registrándolo como cliente y pidiendo al responsable de la base que cambie su rol con `UPDATE usuario SET rol = 'empleado' WHERE correo = '...';` desde el SQL Editor (el cambio tiene efecto inmediato).

## 10. Despliegue en Render (futuro; no realizado)

| Ajuste | Valor |
|---|---|
| Tipo | Web Service (Python) |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --workers 2 --bind 0.0.0.0:$PORT "app:create_app()"` |
| Health Check Path | `/api/health` |
| Variables | `APP_ENV=production`, `PYTHON_VERSION=3.14.3`, `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL` (production, `fullbikers_app`), `CORS_ORIGINS` (URL de Netlify) |

El catálogo ya se registra en producción porque exige autenticación. El administrador de producción se crea ejecutando `crear-admin` localmente con la `DATABASE_URL` de `production` (solo el responsable) o desde la *Shell* de Render.

## 11. Nuevo colaborador: lista de pasos

1. Clonar el repositorio y crear una rama desde `main` actualizado (`git switch main; git pull; git switch -c feature/<modulo>-<descripcion>`).
2. Seguir §4 (entorno virtual y dependencias).
3. Pedir al responsable la `DATABASE_URL` de `development` y pegarla en `backend/.env`. Generar `SECRET_KEY` y `JWT_SECRET_KEY` propias (§5).
4. `python -m pytest -m "not integracion"` y `flask --app app run --debug`; comprobar `/api/health/db`.
5. Crear (o pedir) usuarios de prueba (§9.3) y probar el login (§6.1).
6. Para un endpoint nuevo: controlador → servicio → DAO, protegido con `requiere_rol` (§8) y documentado en `API.md`.
7. Nunca subir `.env`; nunca usar credenciales de `production` en local; nunca ejecutar las pruebas de integración contra Neon.
