"""Punto de entrada de la API FullBikers (Application Factory).

Desarrollo (Windows):   flask --app app run --debug
Producción (Render):    gunicorn --bind 0.0.0.0:$PORT "app:create_app()"
"""
import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from config import database
from config.logs import configurar_logging
from config.settings import obtener_configuracion
from controllers.catalogo_controller import catalogo_bp
from controllers.health_controller import health_bp
from middleware.error_handlers import registrar_manejadores

logger = logging.getLogger(__name__)


def create_app(nombre_entorno=None):
    """Crea y configura la aplicación.

    nombre_entorno: "development", "testing" o "production". Si se omite, se
    usa la variable APP_ENV (predeterminado: development).
    """
    if nombre_entorno != "testing":
        # Carga backend/.env si existe; no sobrescribe variables ya definidas
        # (en Render las variables vienen del panel, no de un archivo).
        load_dotenv(override=False)

    configuracion = obtener_configuracion(nombre_entorno)
    configurar_logging(configuracion.LOG_LEVEL)

    app = Flask(__name__)
    app.config.from_object(configuracion)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    registrar_manejadores(app)
    database.init_app(app)

    app.register_blueprint(health_bp)
    _registrar_blueprints_funcionales(app)

    logger.info("API FullBikers iniciada (entorno: %s).", app.config["APP_ENV"])
    return app


def _registrar_blueprints_funcionales(app):
    # Salvaguarda temporal: el catálogo aún no exige autenticación, por lo que
    # no se expone en producción. Al proteger sus rutas con el middleware de
    # autenticación (siguiente etapa) se elimina esta condición.
    if app.config["APP_ENV"] == "production":
        logger.warning("Catálogo no registrado en producción hasta implementar la autenticación obligatoria.")
        return
    app.register_blueprint(catalogo_bp)


if __name__ == "__main__":
    # Alternativa a "flask run". Escucha solo en localhost; el modo debug se
    # activa únicamente si FLASK_DEBUG=1 en el entorno.
    aplicacion = create_app()
    aplicacion.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
