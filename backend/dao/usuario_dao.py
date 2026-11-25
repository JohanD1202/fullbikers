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
    def existe_correo_de_otro(conn, correo, id_usuario):
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM usuario WHERE correo = %s AND id_usuario <> %s;", (correo, id_usuario))
            return cur.fetchone() is not None

    @staticmethod
    def actualizar_datos_personales(conn, id_usuario, cambios):
        """Actualiza nombre, apellido, correo y/o teléfono (RF-10) y devuelve el usuario.

        `cambios` solo puede contener esas cuatro columnas (lista blanca: los
        nombres de columna nunca provienen del cliente).
        """
        columnas = [c for c in ("nombre", "apellido", "correo", "telefono") if c in cambios]
        if not columnas:
            return UsuarioDAO.obtener_por_id(conn, id_usuario)
        asignaciones = ", ".join(f"{c} = %s" for c in columnas)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE usuario SET {asignaciones} WHERE id_usuario = %s AND activo RETURNING {_COLUMNAS};",
                (*[cambios[c] for c in columnas], id_usuario),
            )
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
