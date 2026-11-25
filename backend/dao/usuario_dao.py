# Consultas SQL de la tabla usuario.
#
# Reglas de la capa DAO (ver config/database.py): reciben la conexión como
# primer argumento, solo SQL parametrizado, sin commit ni rollback.
# El correo se recibe ya normalizado (minúsculas, sin espacios extremos):
# así lo exige el CHECK ck_usuario_correo_normalizado.
from models.usuario import Usuario

_COLUMNAS = "id_usuario, nombre, apellido, correo, contrasena_hash, telefono, rol, activo, fecha_registro"


class UsuarioDAO:
    @staticmethod
    def obtener_por_correo(conn, correo):
        """Usuario (activo o no) con ese correo, incluido el hash; o None."""
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_COLUMNAS} FROM usuario WHERE correo = %s;", (correo,))
            fila = cur.fetchone()
        return Usuario.desde_fila(fila) if fila else None

    @staticmethod
    def obtener_por_id(conn, id_usuario):
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_COLUMNAS} FROM usuario WHERE id_usuario = %s;", (id_usuario,))
            fila = cur.fetchone()
        return Usuario.desde_fila(fila) if fila else None

    @staticmethod
    def crear(conn, nombre, apellido, correo, contrasena_hash, telefono, rol):
        """Inserta un usuario activo y lo devuelve. id_usuario lo genera PostgreSQL."""
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO usuario (nombre, apellido, correo, contrasena_hash, telefono, rol)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {_COLUMNAS};
                """,
                (nombre, apellido, correo, contrasena_hash, telefono, rol),
            )
            fila = cur.fetchone()
        return Usuario.desde_fila(fila)
