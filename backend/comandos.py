"""Comandos de consola de Flask.

    flask --app app crear-admin               Crea el administrador inicial.
    flask --app app crear-usuarios-prueba     Crea un usuario por rol (solo development).

Usan la DATABASE_URL de backend/.env. Las contraseñas se piden de forma
interactiva y oculta; nunca se reciben como argumento ni se guardan en archivos.
Ningún comando modifica usuarios existentes: si el correo ya está registrado,
se informa y no se cambia nada (no se convierte a nadie en administrador).
"""
import click

from exceptions import ApiError, BaseDeDatosNoDisponibleError
from models.usuario import ADMINISTRADOR, CLIENTE, EMPLEADO
from services import usuario_service

# Usuarios de prueba para development. Dominio .test: reservado, nunca real.
USUARIOS_PRUEBA = (
    {"nombre": "Cliente", "apellido": "Prueba", "correo": "cliente@fullbikers.test", "rol": CLIENTE},
    {"nombre": "Empleado", "apellido": "Prueba", "correo": "empleado@fullbikers.test", "rol": EMPLEADO},
    {"nombre": "Administrador", "apellido": "Prueba", "correo": "admin@fullbikers.test", "rol": ADMINISTRADOR},
)


def _pedir_contrasena():
    return click.prompt(
        "Contraseña (8 a 128 caracteres, con letras y números)",
        hide_input=True,
        confirmation_prompt="Confirme la contraseña",
    )


def _describir_error(exc):
    mensaje = exc.mensaje
    campos = (exc.detalles or {}).get("campos")
    if isinstance(campos, dict):
        mensaje += "".join(f"\n  - {campo}: {texto}" for campo, texto in campos.items())
    return mensaje


def registrar_comandos(app):
    @app.cli.command("crear-admin")
    @click.option("--nombre", prompt="Nombre", help="Nombre del administrador.")
    @click.option("--apellido", prompt="Apellido", help="Apellido del administrador.")
    @click.option("--correo", prompt="Correo electrónico", help="Correo de acceso.")
    @click.option("--telefono", prompt="Teléfono (opcional, Enter para omitir)", default="",
                  show_default=False, help="Teléfono de contacto.")
    def crear_admin(nombre, apellido, correo, telefono):
        """Crea un usuario ADMINISTRADOR activo (administrador inicial)."""
        datos = {"nombre": nombre, "apellido": apellido, "correo": correo,
                 "telefono": telefono, "contrasena": _pedir_contrasena()}
        try:
            usuario = usuario_service.crear_usuario(datos, rol=ADMINISTRADOR)
        except ApiError as exc:
            raise click.ClickException(_describir_error(exc)) from None
        except BaseDeDatosNoDisponibleError:
            raise click.ClickException("No hay conexión con PostgreSQL. Revise DATABASE_URL en backend/.env.") from None
        click.echo(f"Administrador creado: id_usuario={usuario.id_usuario}, correo={usuario.correo}.")

    @app.cli.command("crear-usuarios-prueba")
    def crear_usuarios_prueba():
        """Crea un cliente, un empleado y un administrador de prueba (solo development).

        Correos: cliente@, empleado@ y admin@fullbikers.test. Los tres usan la
        contraseña que se escriba al ejecutar el comando. Si un correo ya existe
        se omite sin modificarlo.
        """
        if app.config["APP_ENV"] != "development":
            raise click.ClickException("Este comando solo se permite con APP_ENV=development.")
        contrasena = _pedir_contrasena()
        problema = usuario_service.validar_contrasena(contrasena)
        if problema:
            raise click.ClickException(problema)
        for plantilla in USUARIOS_PRUEBA:
            datos = {**plantilla, "contrasena": contrasena}
            rol = datos.pop("rol")
            try:
                usuario = usuario_service.crear_usuario(datos, rol=rol)
            except ApiError as exc:
                if exc.codigo == "correo_ya_registrado":
                    click.echo(f"Omitido (ya existe): {plantilla['correo']}")
                    continue
                raise click.ClickException(_describir_error(exc)) from None
            except BaseDeDatosNoDisponibleError:
                raise click.ClickException("No hay conexión con PostgreSQL. Revise DATABASE_URL en backend/.env.") from None
            click.echo(f"Creado: {usuario.correo} (rol {usuario.rol}, id_usuario={usuario.id_usuario})")
