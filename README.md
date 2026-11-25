# FullBikers

Aplicación web de comercio electrónico B2C para **FullBikers**, una empresa de Tuluá (Valle del Cauca, Colombia) dedicada a la venta de artículos y accesorios para motociclistas: cascos, guantes, chaquetas con protecciones y equipamiento para la motocicleta.

Proyecto académico de la asignatura **Desarrollo de Software I**, Tecnología en Desarrollo de Software, Facultad de Ingeniería, Universidad del Valle, sede Tuluá (2026).

## Objetivo

Desarrollar una aplicación web que permita a FullBikers gestionar y comercializar sus productos por Internet y vender a nivel nacional, sin depender de un punto físico ni de canales informales.

La aplicación permite:

- a los **clientes**, consultar el catálogo, buscar y filtrar productos, gestionar sus datos, su carrito y sus direcciones, registrar pedidos y seguir su estado;
- a los **empleados**, consultar, verificar, confirmar y actualizar pedidos, consultar el inventario, registrar entradas, salidas y ajustes, y consultar alertas de bajo inventario;
- a los **administradores**, todo lo anterior, además de gestionar usuarios, categorías, productos, variantes, precios e imágenes, y consultar reportes.

**Autenticación obligatoria.** Todos los usuarios deben iniciar sesión para usar cualquier funcionalidad, incluido el catálogo. No existe catálogo público ni rol de visitante. El registro público crea únicamente cuentas de **cliente**; los empleados y administradores se crean mediante procedimientos administrativos. La autorización se verifica siempre en el backend.

## Stack tecnológico

| Capa | Tecnología | Despliegue |
|---|---|---|
| Frontend | React | Netlify |
| Backend | Python con Flask (Psycopg 3) | Render |
| Base de datos | PostgreSQL 18.7 | Neon |
| Control de versiones | Git y GitHub | — |

## Arquitectura

El sistema sigue una arquitectura **cliente-servidor** en tres capas:

```
React (Netlify)  ──HTTP/JSON──▶  Flask (Render)  ──SQL──▶  PostgreSQL (Neon)
     Vista                     Controlador + Modelo + DAO       Datos
```

- **MVC (Modelo-Vista-Controlador):** React implementa la vista; Flask expone los controladores (rutas de la API) y los modelos con las reglas de negocio.
- **DAO (Data Access Object):** el acceso a PostgreSQL se concentra en clases DAO con consultas parametrizadas, separadas de la lógica de negocio.
- **Base de datos:** el esquema garantiza la integridad con claves foráneas, restricciones `CHECK` e índices únicos. La lógica de negocio compleja (flujo de pedidos, descuento y devolución de stock, permisos por rol) vive en el backend. El detalle está en [`database/README.md`](database/README.md).

## Estructura de carpetas

```
.
├── .github/
│   └── CODEOWNERS          # Responsables de revisión del repositorio
├── backend/                # API Flask (MVC + DAO + servicios) — ver backend/README.md
│   ├── API.md              # Contratos REST para el frontend
│   ├── app.py              # Application Factory (create_app)
│   ├── comandos.py         # flask crear-admin / crear-usuarios-prueba
│   ├── config/  controllers/  services/  dao/  models/  middleware/
│   └── tests/              # Pruebas unitarias; tests/integracion/ usa PostgreSQL local
├── database/
│   ├── schema.sql          # Creación del esquema (10 tablas)
│   ├── verification.sql    # Verificación de solo lectura
│   ├── permissions.sql     # Rol técnico de mínimo privilegio
│   ├── seed_dev.sql        # Datos ficticios, solo rama development
│   └── README.md           # Documentación del modelo de datos
├── frontend/               # Aplicación React (Vite + JavaScript), aún sin inicializar
├── .gitignore
└── README.md
```

Los documentos académicos (documento del proyecto, enunciado y plantilla) se mantienen fuera del repositorio.

## Estado del desarrollo

| Componente | Estado |
|---|---|
| Base de datos | Esquema aplicado en Neon (`production`) y verificado manualmente por el equipo con `verification.sql` |
| Backend | Infraestructura (factory, configuración, pool Psycopg 3, errores), autenticación JWT con roles (registro de clientes, login, logout, usuario actual), catálogo protegido y comando para el administrador inicial. Probado con pruebas unitarias y de integración sobre PostgreSQL 18 local. Pendiente: perfil, direcciones, carrito, pedidos, inventario y administración |
| Frontend | Sin inicializar; puede implementar login, registro, rutas protegidas, menú por rol y catálogo con los contratos de [`backend/API.md`](backend/API.md) |

Instalación, variables de entorno, ejecución y pruebas del backend: [`backend/README.md`](backend/README.md).

## Configuración y secretos

Las credenciales (cadena de conexión a Neon, claves de sesión y similares) **no se versionan**. Cada componente usa un archivo `.env` local, excluido por `.gitignore`, y publica un `.env.example` con los nombres de las variables y sin valores reales (ver [`backend/.env.example`](backend/.env.example)). En producción, los valores se configuran como variables de entorno en Render y Netlify.

Entornos de base de datos en Neon: la rama `development` para el desarrollo local y las pruebas del equipo, y la rama `production` reservada para la aplicación desplegada. La API se conecta con el rol técnico `fullbikers_app` (sin permisos de borrado ni de estructura), nunca con el propietario.

## Autenticación y roles

Todo el sistema exige iniciar sesión (no hay catálogo público). Los usuarios se autentican con un token JWT de 60 minutos que el frontend guarda en `sessionStorage` y envía como `Authorization: Bearer <token>`. Roles: `cliente` (registro público), `empleado` y `administrador` (acceso total). El primer administrador se crea con `flask --app app crear-admin`. Cerrar sesión borra el token del navegador; un token copiado seguiría siendo válido hasta expirar, limitación aceptada para el alcance académico. Detalles: [`backend/README.md`](backend/README.md) §8 y [`backend/API.md`](backend/API.md).

## Base de datos

El esquema se ejecuta manualmente en Neon. Las instrucciones, las decisiones de diseño y las diferencias frente al modelo entidad-relación están en [`database/README.md`](database/README.md).

## Equipo

| Integrante | Rol |
|---|---|
| Juan Sebastián Figueroa Valladales | Scrum Master y responsable de la base de datos |
| Johan Daniel Idárraga Hincapié | Desarrollador back-end y servicios |
| Miguel Ángel Sánchez Vera | Desarrollador front-end |

Docente: Ing. Luis Adrián Lasso C., M.Sc.
