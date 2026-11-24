# FullBikers

Aplicación web de comercio electrónico B2C para **FullBikers**, una empresa de Tuluá (Valle del Cauca, Colombia) dedicada a la venta de artículos y accesorios para motociclistas: cascos, guantes, chaquetas con protecciones y equipamiento para la motocicleta.

Proyecto académico de la asignatura **Desarrollo de Software I**, Tecnología en Desarrollo de Software, Facultad de Ingeniería, Universidad del Valle, sede Tuluá (2026).

## Objetivo

Desarrollar una aplicación web que permita a FullBikers gestionar y comercializar sus productos por Internet y vender a nivel nacional, sin depender de un punto físico ni de canales informales.

La aplicación permite:

- a los **clientes**, consultar el catálogo, buscar y filtrar productos, gestionar su carrito y sus direcciones, registrar pedidos y seguir su estado;
- a los **empleados**, verificar, confirmar y actualizar pedidos y registrar movimientos de inventario;
- a los **administradores**, gestionar usuarios, categorías, productos, variantes, precios e imágenes, y consultar reportes de ventas y alertas de bajo inventario.

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
├── backend/                # API Flask (MVC + DAO), aún sin inicializar
├── database/
│   ├── schema.sql          # Creación del esquema (10 tablas)
│   ├── verification.sql    # Verificación de solo lectura
│   └── README.md           # Documentación del modelo de datos
├── docs/
│   ├── academico/          # Documento del proyecto, enunciado y plantilla
│   └── diagramas/          # Diagramas exportados (MER, clases, casos de uso)
├── frontend/               # Aplicación React, aún sin inicializar
├── .gitignore
└── README.md
```

## Configuración y secretos

Las credenciales (cadena de conexión a Neon, claves de sesión y similares) **no se versionan**. Cada componente usará un archivo `.env` local, excluido por `.gitignore`, y publicará un `.env.example` con los nombres de las variables y sin valores reales. En producción, los valores se configuran como variables de entorno en Render y Netlify.

## Base de datos

El esquema se ejecuta manualmente en Neon. Las instrucciones, las decisiones de diseño y las diferencias frente al modelo entidad-relación están en [`database/README.md`](database/README.md).

## Equipo

| Integrante | Rol |
|---|---|
| Juan Sebastián Figueroa Valladales | Scrum Master y responsable de la base de datos |
| Johan Daniel Idárraga Hincapié | Desarrollador back-end y servicios |
| Miguel Ángel Sánchez Vera | Desarrollador front-end |

Docente: Ing. Luis Adrián Lasso C., M.Sc.
