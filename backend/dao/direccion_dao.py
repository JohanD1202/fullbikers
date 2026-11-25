# Consultas SQL de la tabla direccion (RF-11).
#
# Reglas DAO: conexión como primer argumento, SQL parametrizado, sin commit ni
# rollback. TODAS las consultas filtran por id_usuario: una dirección ajena se
# comporta igual que una inexistente (None).
from models.direccion import Direccion

_COLUMNAS = "id_direccion, id_usuario, departamento, municipio, direccion, complemento, codigo_postal, principal, activo"
# Columnas que el usuario puede escribir (lista blanca para el UPDATE dinámico).
COLUMNAS_EDITABLES = ("departamento", "municipio", "direccion", "complemento", "codigo_postal", "principal")


class DireccionDAO:
    @staticmethod
    def bloquear_usuario(conn, id_usuario):
        """Serializa las operaciones sobre las direcciones de un usuario.

        Bloquea la fila del usuario hasta el fin de la transacción, de modo que
        dos peticiones simultáneas no marquen dos direcciones principales.
        FOR NO KEY UPDATE no bloquea las inserciones que referencian al usuario.
        """
        with conn.cursor() as cur:
            cur.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s FOR NO KEY UPDATE;", (id_usuario,))

    @staticmethod
    def listar_activas(conn, id_usuario):
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNAS} FROM direccion WHERE id_usuario = %s AND activo "
                "ORDER BY principal DESC, id_direccion ASC;",
                (id_usuario,),
            )
            return [Direccion.desde_fila(f) for f in cur.fetchall()]

    @staticmethod
    def obtener_activa(conn, id_direccion, id_usuario):
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNAS} FROM direccion WHERE id_direccion = %s AND id_usuario = %s AND activo;",
                (id_direccion, id_usuario),
            )
            fila = cur.fetchone()
        return Direccion.desde_fila(fila) if fila else None

    @staticmethod
    def contar_activas(conn, id_usuario):
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS total FROM direccion WHERE id_usuario = %s AND activo;", (id_usuario,))
            return cur.fetchone()["total"]

    @staticmethod
    def desmarcar_principal(conn, id_usuario):
        """Quita la marca de principal a la dirección activa que la tenga."""
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE direccion SET principal = FALSE WHERE id_usuario = %s AND principal AND activo;",
                (id_usuario,),
            )

    @staticmethod
    def crear(conn, id_usuario, datos):
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO direccion (id_usuario, departamento, municipio, direccion, complemento, codigo_postal, principal)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING {_COLUMNAS};
                """,
                (id_usuario, datos["departamento"], datos["municipio"], datos["direccion"],
                 datos.get("complemento"), datos.get("codigo_postal"), datos.get("principal", False)),
            )
            return Direccion.desde_fila(cur.fetchone())

    @staticmethod
    def actualizar(conn, id_direccion, id_usuario, cambios):
        columnas = [c for c in COLUMNAS_EDITABLES if c in cambios]
        asignaciones = ", ".join(f"{c} = %s" for c in columnas)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE direccion SET {asignaciones} WHERE id_direccion = %s AND id_usuario = %s AND activo "
                f"RETURNING {_COLUMNAS};",
                (*[cambios[c] for c in columnas], id_direccion, id_usuario),
            )
            fila = cur.fetchone()
        return Direccion.desde_fila(fila) if fila else None

    @staticmethod
    def desactivar(conn, id_direccion, id_usuario):
        """Borrado lógico. También quita "principal" (CHECK ck_direccion_principal_activa)."""
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE direccion SET activo = FALSE, principal = FALSE "
                "WHERE id_direccion = %s AND id_usuario = %s AND activo RETURNING id_direccion;",
                (id_direccion, id_usuario),
            )
            return cur.fetchone() is not None
