# Clase de dominio Direccion (tabla direccion de database/schema.sql).


class Direccion:
    def __init__(self, id_direccion, id_usuario, departamento, municipio, direccion,
                 complemento=None, codigo_postal=None, principal=False, activo=True):
        self.id_direccion = id_direccion
        self.id_usuario = id_usuario
        self.departamento = departamento
        self.municipio = municipio
        self.direccion = direccion
        self.complemento = complemento
        self.codigo_postal = codigo_postal
        self.principal = principal
        self.activo = activo

    @classmethod
    def desde_fila(cls, fila):
        return cls(**{k: fila[k] for k in (
            "id_direccion", "id_usuario", "departamento", "municipio", "direccion",
            "complemento", "codigo_postal", "principal", "activo")})

    def to_dict(self):
        # id_usuario y activo no se exponen: siempre son del usuario autenticado
        # y las direcciones inactivas no se devuelven.
        return {
            "id_direccion": self.id_direccion,
            "departamento": self.departamento,
            "municipio": self.municipio,
            "direccion": self.direccion,
            "complemento": self.complemento,
            "codigo_postal": self.codigo_postal,
            "principal": self.principal,
        }
