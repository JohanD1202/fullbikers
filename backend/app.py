"""Punto de entrada de la API FullBikers (Application Factory).

Desarrollo (Windows):   flask --app app run --debug
Producción (Render):    gunicorn --bind 0.0.0.0:$PORT "app:create_app()"
Administrador inicial:  flask --app app crear-admin
"""
import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

import comandos
from config import database
from config.logs import configurar_logging
from config.settings import obtener_configuracion
from controllers.auth_controller import auth_bp
from controllers.carrito_controller import carrito_bp
from controllers.catalogo_controller import catalogo_bp
from controllers.direccion_controller import direccion_bp
from controllers.health_controller import health_bp
from controllers.pedido_controller import pedido_bp
from controllers.perfil_controller import perfil_bp
from middleware import auth
from middleware.error_handlers import registrar_manejadores
from services import auth_service

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
    auth.init_app(app)
    auth_service.init_app(app)
    database.init_app(app)

    # Públicos: diagnóstico, registro e inicio de sesión. El resto de rutas
    # se protege con los decoradores de middleware/auth.py.
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogo_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(direccion_bp)
    app.register_blueprint(carrito_bp)
    app.register_blueprint(pedido_bp)
    comandos.registrar_comandos(app)

    logger.info("API FullBikers iniciada (entorno: %s).", app.config["APP_ENV"])
    return app


if __name__ == "__main__":
    # Alternativa a "flask run". Escucha solo en localhost; el modo debug se
    # activa únicamente si FLASK_DEBUG=1 en el entorno.
    aplicacion = create_app()
    aplicacion.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
