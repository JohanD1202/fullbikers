# Clase de dominio Usuario. Los atributos siguen la tabla usuario de
# database/schema.sql. El hash de la contraseña nunca se serializa.

CLIENTE = "cliente"
EMPLEADO = "empleado"
ADMINISTRADOR = "administrador"
ROLES = (CLIENTE, EMPLEADO, ADMINISTRADOR)


class Usuario:
    def __init__(self, id_usuario, nombre, apellido, correo, rol, activo=True,
                 telefono=None, contrasena_hash=None, fecha_registro=None):
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.apellido = apellido
        self.correo = correo
        self.telefono = telefono
        self.rol = rol
        self.activo = activo
        self.contrasena_hash = contrasena_hash
        self.fecha_registro = fecha_registro

    @classmethod
    def desde_fila(cls, fila):
        return cls(
            id_usuario=fila["id_usuario"],
            nombre=fila["nombre"],
            apellido=fila["apellido"],
            correo=fila["correo"],
            telefono=fila.get("telefono"),
            rol=fila["rol"],
            activo=fila["activo"],
            contrasena_hash=fila.get("contrasena_hash"),
            fecha_registro=fila.get("fecha_registro"),
        )

    @property
    def es_administrador(self):
        return self.rol == ADMINISTRADOR

    def to_dict(self):
        """Datos públicos del usuario. Nunca incluye contrasena_hash."""
        return {
            "id_usuario": self.id_usuario,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "correo": self.correo,
            "telefono": self.telefono,
            "rol": self.rol,
        }

    def __repr__(self):
        # Evita que el hash termine en logs o trazas.
        return f"Usuario(id_usuario={self.id_usuario!r}, rol={self.rol!r}, activo={self.activo!r})"
