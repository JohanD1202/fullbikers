"""Configuración de la API por entorno: development, testing y production.

Los valores se leen de variables de entorno (ver backend/.env.example).
La configuración de producción valida los secretos y rechaza valores
ausentes, débiles o de ejemplo.
"""
import os
import secrets


class ConfiguracionInvalidaError(RuntimeError):
    """La configuración del entorno no permite arrancar la aplicación."""


# Fragmentos que delatan un valor de ejemplo copiado de la documentación.
_MARCADORES_DE_EJEMPLO = ("cambiar", "changeme", "ejemplo", "example", "secret", "<", "xxx")
_LONGITUD_MINIMA_SECRETO = 32


def _texto(nombre, predeterminado=None):
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return predeterminado
    return valor.strip()


def _entero(nombre, predeterminado, minimo, maximo):
    valor = _texto(nombre)
    if valor is None:
        return predeterminado
    try:
        numero = int(valor)
    except ValueError as exc:
        raise ConfiguracionInvalidaError(f"{nombre} debe ser un número entero.") from exc
    if not minimo <= numero <= maximo:
        raise ConfiguracionInvalidaError(f"{nombre} debe estar entre {minimo} y {maximo}.")
    return numero


def _lista(nombre, predeterminado):
    valor = _texto(nombre)
    if valor is None:
        return list(predeterminado)
    return [origen.strip().rstrip("/") for origen in valor.split(",") if origen.strip()]


class BaseConfig:
    APP_ENV = "base"
    DEBUG = False
    TESTING = False

    # Valores por defecto de la API.
    PAGINA_TAMANO_PREDETERMINADO = 12
    PAGINA_TAMANO_MAXIMO = 50
    BUSQUEDA_LONGITUD_MAXIMA = 100

    def __init__(self):
        self.SECRET_KEY = _texto("SECRET_KEY")
        self.JWT_SECRET_KEY = _texto("JWT_SECRET_KEY")
        self.DATABASE_URL = _texto("DATABASE_URL")
        self.CORS_ORIGINS = _lista("CORS_ORIGINS", ["http://localhost:5173"])
        self.DB_POOL_MIN_SIZE = _entero("DB_POOL_MIN_SIZE", 0, 0, 20)
        self.DB_POOL_MAX_SIZE = _entero("DB_POOL_MAX_SIZE", 5, 1, 20)
        self.DB_CONNECT_TIMEOUT = _entero("DB_CONNECT_TIMEOUT", 10, 1, 60)
        self.LOG_LEVEL = (_texto("LOG_LEVEL", "INFO")).upper()
        if self.DB_POOL_MIN_SIZE > self.DB_POOL_MAX_SIZE:
            raise ConfiguracionInvalidaError("DB_POOL_MIN_SIZE no puede ser mayor que DB_POOL_MAX_SIZE.")

    def validar(self):
        """Comprobaciones adicionales propias de cada entorno."""


class DevelopmentConfig(BaseConfig):
    APP_ENV = "development"

    def __init__(self):
        super().__init__()
        # Sin secreto definido se genera uno efímero: los tokens dejan de ser
        # válidos al reiniciar, lo cual es aceptable en desarrollo.
        self.SECRET_KEY = self.SECRET_KEY or secrets.token_urlsafe(48)
        self.JWT_SECRET_KEY = self.JWT_SECRET_KEY or secrets.token_urlsafe(48)


class TestingConfig(BaseConfig):
    APP_ENV = "testing"
    TESTING = True

    def __init__(self):
        super().__init__()
        # Las pruebas nunca usan la base real aunque exista un .env local.
        self.DATABASE_URL = None
        self.SECRET_KEY = "clave-solo-para-pruebas-automatizadas-0001"
        self.JWT_SECRET_KEY = "jwt-solo-para-pruebas-automatizadas-0001"
        self.CORS_ORIGINS = ["http://localhost:5173"]
        self.LOG_LEVEL = "WARNING"


class ProductionConfig(BaseConfig):
    APP_ENV = "production"

    def validar(self):
        errores = []
        for nombre in ("SECRET_KEY", "JWT_SECRET_KEY"):
            problema = _problema_secreto(getattr(self, nombre))
            if problema:
                errores.append(f"{nombre} {problema}.")
        if self.SECRET_KEY and self.SECRET_KEY == self.JWT_SECRET_KEY:
            errores.append("SECRET_KEY y JWT_SECRET_KEY deben ser distintas.")
        if not self.DATABASE_URL:
            errores.append("DATABASE_URL es obligatoria.")
        elif "sslmode=require" not in self.DATABASE_URL and "sslmode=verify" not in self.DATABASE_URL:
            errores.append("DATABASE_URL debe incluir sslmode=require (o verify-full).")
        if not self.CORS_ORIGINS or "*" in self.CORS_ORIGINS:
            errores.append("CORS_ORIGINS debe listar orígenes explícitos (no se admite '*').")
        if errores:
            # Los mensajes nombran variables, nunca sus valores.
            raise ConfiguracionInvalidaError("Configuración de producción inválida: " + " ".join(errores))


def _problema_secreto(valor):
    if not valor:
        return "es obligatoria"
    if len(valor) < _LONGITUD_MINIMA_SECRETO:
        return f"debe tener al menos {_LONGITUD_MINIMA_SECRETO} caracteres"
    if any(marcador in valor.lower() for marcador in _MARCADORES_DE_EJEMPLO):
        return "parece un valor de ejemplo"
    return None


_CONFIGURACIONES = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def obtener_configuracion(nombre=None):
    """Devuelve la configuración del entorno indicado o del definido en APP_ENV."""
    nombre = (nombre or _texto("APP_ENV", "development")).lower()
    clase = _CONFIGURACIONES.get(nombre)
    if clase is None:
        raise ConfiguracionInvalidaError(
            f"APP_ENV desconocido: '{nombre}'. Valores válidos: {', '.join(_CONFIGURACIONES)}."
        )
    configuracion = clase()
    configuracion.validar()
    return configuracion
