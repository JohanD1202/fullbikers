"""Pruebas unitarias de los comandos crear-admin y crear-usuarios-prueba."""
import pytest

from app import create_app
from models.usuario import ADMINISTRADOR, CLIENTE

ENTRADA_ADMIN = "Laura\nGómez\n  Admin@FullBikers.test \n\nClave2026\nClave2026\n"


def _ejecutar(app, args, entrada):
    return app.test_cli_runner().invoke(args=args, input=entrada)


def test_crear_admin_crea_administrador_activo(app, repositorio):
    resultado = _ejecutar(app, ["crear-admin"], ENTRADA_ADMIN)
    assert resultado.exit_code == 0, resultado.output
    usuario = repositorio.filas[1]
    assert (usuario.rol, usuario.activo, usuario.correo) == (ADMINISTRADOR, True, "admin@fullbikers.test")
    assert usuario.contrasena_hash.startswith("scrypt:")
    # La contraseña se pide oculta: no aparece en la salida.
    assert "Clave2026" not in resultado.output


def test_crear_admin_contrasenas_distintas_se_vuelve_a_pedir(app, repositorio):
    entrada = "Laura\nGómez\nadmin@fullbikers.test\n\nClave2026\nOtra2026\nClave2026\nClave2026\n"
    resultado = _ejecutar(app, ["crear-admin"], entrada)
    assert resultado.exit_code == 0, resultado.output
    assert len(repositorio.filas) == 1


def test_crear_admin_no_promueve_usuario_existente(app, repositorio):
    existente = repositorio.agregar("admin@fullbikers.test", rol=CLIENTE)
    resultado = _ejecutar(app, ["crear-admin"], ENTRADA_ADMIN)
    assert resultado.exit_code == 1
    assert "Ya existe" in resultado.output
    assert existente.rol == CLIENTE
    assert len(repositorio.filas) == 1


def test_crear_admin_datos_invalidos(app, repositorio):
    resultado = _ejecutar(app, ["crear-admin", "--nombre", "L", "--apellido", "G",
                                "--correo", "no-es-correo", "--telefono", ""], "corta\ncorta\n")
    assert resultado.exit_code == 1
    assert "correo" in resultado.output and "contrasena" in resultado.output
    assert repositorio.filas == {}


def test_crear_usuarios_prueba_rechazado_fuera_de_development(app, repositorio):
    resultado = _ejecutar(app, ["crear-usuarios-prueba"], "Clave2026\nClave2026\n")
    assert resultado.exit_code == 1
    assert "development" in resultado.output
    assert repositorio.filas == {}


@pytest.fixture
def app_desarrollo():
    return create_app("development")


def test_crear_usuarios_prueba_tres_roles_y_repetible(app_desarrollo, repositorio):
    resultado = _ejecutar(app_desarrollo, ["crear-usuarios-prueba"], "Clave2026\nClave2026\n")
    assert resultado.exit_code == 0, resultado.output
    assert sorted(u.rol for u in repositorio.filas.values()) == ["administrador", "cliente", "empleado"]

    segunda = _ejecutar(app_desarrollo, ["crear-usuarios-prueba"], "Clave2026\nClave2026\n")
    assert segunda.exit_code == 0
    assert segunda.output.count("Omitido") == 3
    assert len(repositorio.filas) == 3
