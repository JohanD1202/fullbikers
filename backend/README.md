# FullBikers — Backend (API REST con Flask)

API REST de FullBikers: Flask + Psycopg 3 sobre PostgreSQL (Neon), con arquitectura MVC, patrón DAO y capa de servicios. La vista es la aplicación React del directorio `frontend/`.

Contratos de la API para el frontend: [`API.md`](API.md).

## 1. Estado actual

| Componente | Estado |
|---|---|
| Application Factory, configuración por entorno, errores JSON, logging, CORS | Implementado y probado con pruebas unitarias |
| Pool de conexiones Psycopg 3 y transacciones compartidas entre DAO | Implementado; **sin verificar contra Neon** |
| `GET /api/health`, `GET /api/health/db` | Implementados |
| Catálogo (`/api/principal`, `/api/productos`, `/api/productos/{id}`) | Implementado solo para desarrollo local. **No terminado**: falta la autenticación obligatoria. No se registra en producción. |
| Autenticación y autorización | Diseño propuesto (§8), pendiente de aprobación |
| Perfil, direcciones, carrito, pedidos, administración | Pendientes |

## 2. Arquitectura

```
React (vista) ──HTTP/JSON──▶ controllers ──▶ services ──▶ dao ──SQL──▶ PostgreSQL
                                  │              │          │
                             validan         reglas de   SQL parametrizado,
                             parámetros y    negocio y   sin commit/rollback
                             responden       transacción
                                     models: entidades y serialización
```

| Capa | Responsabilidad | No hace |
|---|---|---|
| `controllers/` | Rutas (Blueprints), validación de parámetros, respuesta HTTP | SQL ni reglas de negocio |
| `services/` | Casos de uso; abren la conexión o la transacción y coordinan uno o varios DAO | HTTP |
| `dao/` | Consultas SQL parametrizadas; reciben la conexión como primer argumento | `commit`, `rollback`, abrir conexiones |
| `models/` | Entidades (`Producto`, `Categoria`, ...) y su serialización (`to_dict`) | Acceso a datos |
| `middleware/` | Manejo centralizado de errores; en la siguiente etapa, autenticación | — |
| `config/` | Configuración por entorno, pool de conexiones, logging | — |

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
├── exceptions.py               # ApiError y excepciones de dominio
├── config/
│   ├── settings.py             # DevelopmentConfig, TestingConfig, ProductionConfig
│   ├── database.py             # Pool Psycopg 3, obtener_conexion(), transaccion()
│   └── logs.py                 # Logging con ocultamiento de credenciales
├── controllers/
│   ├── health_controller.py    # /api/health, /api/health/db
│   ├── catalogo_controller.py  # /api/principal, /api/productos
│   └── parametros.py           # Validación de parámetros de consulta
├── services/catalogo_service.py
├── dao/producto_dao.py
├── models/{producto.py, dinero.py}
├── middleware/error_handlers.py
├── tests/                      # pytest (sin base de datos)
├── requirements.txt            # dependencias de ejecución
├── requirements-dev.txt        # + pytest
├── pytest.ini
├── .env.example                # plantilla de variables (sin valores reales)
└── API.md                      # contratos REST
```

## 3. Versiones

| Componente | Versión |
|---|---|
| Python | **3.14.3** (local y Render) |
| Flask | 3.1.3 (Werkzeug 3.1.9) |
| flask-cors | 6.0.5 |
| Flask-JWT-Extended | 4.7.4 (instalada para la etapa de autenticación; aún no se usa) |
| psycopg[binary] | 3.3.9 |
| psycopg-pool | 3.3.3 |
| python-dotenv | 1.2.4 |
| gunicorn | 27.0.1 (solo Linux/Render; se omite en Windows) |
| pytest | 9.2.0 (desarrollo) |

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

## 5. Variables de entorno

Se definen en `backend/.env` (excluido de Git) a partir de [`.env.example`](.env.example).

| Variable | Obligatoria | Uso |
|---|---|---|
| `APP_ENV` | No (`development`) | `development`, `testing` o `production` |
| `SECRET_KEY` | Sí en producción | Firma de Flask. ≥ 32 caracteres aleatorios |
| `JWT_SECRET_KEY` | Sí en producción | Firma de JWT. ≥ 32 caracteres, distinta de `SECRET_KEY` |
| `DATABASE_URL` | Sí en producción | Conexión a Neon con el rol `fullbikers_app`, endpoint directo, `sslmode=require` |
| `CORS_ORIGINS` | Sí en producción | Orígenes del frontend separados por comas; `*` no se admite en producción |
| `DB_POOL_MIN_SIZE` / `DB_POOL_MAX_SIZE` | No (0 / 5) | Tamaño del pool por proceso |
| `DB_CONNECT_TIMEOUT` | No (10) | Segundos para conectar u obtener conexión del pool |
| `PORT` | No (5000) | Puerto de `python app.py` y de Gunicorn en Render |
| `LOG_LEVEL` | No (`INFO`) | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Generar un secreto: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

`ProductionConfig` se niega a arrancar si faltan secretos, si son cortos o parecen de ejemplo, si `DATABASE_URL` no exige SSL o si CORS admite `*`. Los mensajes nombran la variable, nunca su valor.

Sin `DATABASE_URL`, la API arranca en desarrollo: `/api/health` responde 200 y los endpoints que usan la base responden 503.

## 6. Ejecución local

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
flask --app app run --debug          # http://127.0.0.1:5000
```

Alternativa: `python app.py` (escucha en `127.0.0.1:$PORT`; modo debug solo si `FLASK_DEBUG=1`). El modo debug nunca queda activado por configuración.

Comprobación: `curl http://127.0.0.1:5000/api/health` y `curl http://127.0.0.1:5000/api/health/db`.

Gunicorn no funciona en Windows; solo se usa en Render.

## 7. Pruebas

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest
```

Las pruebas **no se conectan a ninguna base de datos**: la configuración `testing` ignora `DATABASE_URL` y los DAO se prueban con conexiones falsas. Por eso verifican la construcción de las consultas, no que el SQL funcione en PostgreSQL; eso se comprueba en la verificación de integración contra la rama `development`.

Antes de abrir un Pull Request: `python -m pytest` en verde, la API arranca con `flask --app app run`, y el diff no incluye `.env`, `.venv` ni credenciales.

## 8. Autenticación y autorización (diseño propuesto, pendiente de aprobación)

**Regla general:** todo el sistema exige iniciar sesión. Públicos solo: registro de clientes, login y diagnóstico.

### Roles funcionales vs. roles técnicos

| Rol funcional (columna `usuario.rol`) | Responsabilidades | RF de referencia |
|---|---|---|
| `cliente` | Registrarse; iniciar/cerrar sesión; catálogo, búsqueda, filtro y detalle; datos personales; direcciones; carrito; pedidos; historial y estado de sus pedidos | RF-01–RF-21 |
| `empleado` | Iniciar/cerrar sesión; consultar, verificar y confirmar pedidos y actualizar sus estados; consultar inventario; registrar entradas, salidas y ajustes; alertas de stock bajo | RF-08, RF-09, RF-29–RF-34 |
| `administrador` | Todo lo anterior; administrar usuarios, productos, categorías, variantes, precios e imágenes; reportes | Todos |

Los roles técnicos de PostgreSQL son otra cosa: la API se conecta siempre como `fullbikers_app` (sin DDL ni DELETE). Ser administrador de la tienda **no** otorga privilegios de base de datos.

### Archivos previstos

| Archivo | Contenido |
|---|---|
| `models/usuario.py` | `Usuario` con `to_dict()` que **nunca** incluye `contrasena_hash` |
| `dao/usuario_dao.py` | `obtener_por_correo(conn, correo)`, `obtener_por_id(conn, id)`, `crear(conn, ...)`, `actualizar_datos(...)`. Todos parametrizados |
| `services/auth_service.py` | Registro (normaliza y valida; rol fijo `cliente`; hash con `werkzeug.security.generate_password_hash`, scrypt), login (verifica hash y `activo`; emite JWT), usuario actual |
| `controllers/auth_controller.py` | `/api/auth/register`, `/login`, `/logout`, `/me` |
| `middleware/auth.py` | Decorador `requiere_autenticacion(*roles)` |
| `cli.py` | Comandos `flask crear-admin` y `flask crear-usuario --rol empleado` |
| `tests/test_auth_*.py` | Pruebas de los casos de la tabla final |

### Decisiones

1. **JWT de acceso de 60 minutos, sin refresh token.** Identidad (`sub`) = `id_usuario`. Algoritmo HS256 con `JWT_SECRET_KEY`. Incluye `jti` e `iat`.
2. **La autorización no confía en el rol del token.** `requiere_autenticacion` valida el JWT y luego **lee el usuario de la base en cada petición**: si no existe o `activo = false` → `401`; el rol vigente de la base decide el acceso → `403` si no corresponde. Un cambio de rol o una desactivación tienen efecto inmediato. El `administrador` pasa cualquier verificación de rol.
3. **Propiedad de recursos.** Los servicios toman `id_usuario` de `g.usuario` (cargado por el middleware), nunca del cuerpo ni de la URL; las consultas de cliente filtran `WHERE id_usuario = %s`. Un recurso ajeno responde `404`.
4. **Registro solo de clientes.** Lista blanca de campos; `rol`, `activo` o `id_usuario` en el cuerpo → `400 campo_no_permitido`. El `INSERT` fija `rol = 'cliente'`. Correo: `strip().lower()`, formato y longitud; `23505` se traduce a `409 correo_ya_registrado` (RF-07).
5. **Login sin enumeración.** Mismo `401 credenciales_invalidas` para correo inexistente, contraseña incorrecta o cuenta inactiva. Si el correo no existe se verifica contra un hash ficticio para igualar tiempos.
6. **Intentos de inicio de sesión.** Limitador en memoria por correo + IP: 5 fallos en 15 minutos → `429`. Limitación conocida: es por proceso y se reinicia con el servicio; suficiente para el alcance académico sin nuevas tablas ni dependencias.
7. **Almacenamiento en React.** Token en memoria y en `sessionStorage` (sobrevive a recargar, se borra al cerrar la pestaña). Nunca en `localStorage` ni en cookies accesibles. React escapa el contenido; prohibido `dangerouslySetInnerHTML` con datos de usuario. Al recibir `401` el cliente HTTP borra el token y redirige al login ("sesión expirada").
8. **Logout y revocación.** Borrar el token del navegador **no** lo invalida en el servidor. Con el esquema actual:
   - `POST /api/auth/logout` responde `204` y el frontend descarta el token.
   - Riesgo residual: un token copiado sigue siendo válido hasta 60 minutos, **salvo** que el usuario sea desactivado (efecto inmediato por la decisión 2).
   - Mejora opcional (requiere tu autorización por ser un cambio de esquema): migración `V002` con `usuario.sesiones_validas_desde TIMESTAMPTZ`; el logout la actualiza a `now()` y el middleware rechaza tokens con `iat` anterior. Revoca todas las sesiones del usuario y funciona con varios procesos. Una lista negra en memoria no se propone porque falla con varios workers de Gunicorn.
9. **Administrador inicial.** Comando `flask crear-admin`, ejecutado localmente por el responsable con la `DATABASE_URL` de la rama correspondiente: pide correo y contraseña sin mostrarla, la hashea con Werkzeug y crea el usuario con rol `administrador`. Si ya existe un administrador activo, se niega. Así se reemplaza el procedimiento del README de la base de datos (§13: registrarse y luego `UPDATE` manual). Los empleados los crea un administrador desde la API (etapa de administración de usuarios) o con `flask crear-usuario --rol empleado` en desarrollo.
10. **Contraseñas.** 8–128 caracteres, al menos una letra y un número. Nunca se registran en logs ni se devuelven.

### Pruebas mínimas de la etapa

| Caso | Esperado |
|---|---|
| Registro válido | 201, rol `cliente`, sin `contrasena_hash` en la respuesta |
| Registro con `rol: "administrador"` | 400 `campo_no_permitido`; no se crea el usuario |
| Correo duplicado (otra capitalización) | 409 |
| Login correcto / incorrecto / inactivo | 200 / 401 / 401 (mismo mensaje) |
| 6.º intento fallido | 429 |
| Catálogo sin token, con token alterado o expirado | 401 |
| Usuario desactivado con token vigente | 401 |
| Rol cambiado de `administrador` a `cliente` con token vigente | 403 en endpoint de administración |
| Cliente consulta pedido o dirección de otro cliente | 404 |
| Cliente en endpoint de empleado | 403 |
| Administrador en endpoint de empleado | 200 |

## 9. Neon: desarrollo y producción

| Rama de Neon | Uso | Quién usa sus credenciales |
|---|---|---|
| `development` | Desarrollo local y pruebas de integración | Todo el equipo (rol `fullbikers_app` de esa rama) |
| `production` | Solo la API desplegada en Render | Solo Render |

- Conexión: endpoint **directo** (host sin `-pooler`). La API ya tiene su propio pool; ver `database/permissions.sql`.
- Configuración de permisos: [`../database/permissions.sql`](../database/permissions.sql). Datos de prueba: [`../database/seed_dev.sql`](../database/seed_dev.sql) (solo `development`).
- Los colaboradores no necesitan acceso al proyecto de Neon ni al rol propietario: reciben únicamente la `DATABASE_URL` de `development` por un canal privado y la guardan en su `backend/.env`.

## 10. Despliegue en Render (futuro; no realizado)

| Ajuste | Valor |
|---|---|
| Tipo | Web Service (Python) |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --workers 2 --bind 0.0.0.0:$PORT "app:create_app()"` |
| Health Check Path | `/api/health` |
| Variables | `APP_ENV=production`, `PYTHON_VERSION=3.14.3`, `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL` (production, `fullbikers_app`), `CORS_ORIGINS` (URL de Netlify) |

Requisito previo: autenticación obligatoria implementada (hasta entonces el catálogo no se registra en producción).

## 11. Nuevo colaborador: lista de pasos

1. Clonar el repositorio y crear una rama desde `main` actualizado (`git switch main; git pull; git switch -c feature/<modulo>-<descripcion>`).
2. Seguir §4 (entorno virtual y dependencias).
3. Pedir al responsable la `DATABASE_URL` de `development` y pegarla en `backend/.env`. Generar `SECRET_KEY` y `JWT_SECRET_KEY` propias.
4. `python -m pytest` y `flask --app app run --debug`; comprobar `/api/health/db`.
5. Nunca subir `.env`; nunca usar credenciales de `production` en local.
