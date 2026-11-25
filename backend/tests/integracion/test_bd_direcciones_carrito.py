"""Integración (PostgreSQL real): perfil (RF-10), direcciones (RF-11) y carrito (RF-12 a RF-15)."""
import uuid
from decimal import Decimal

import pytest

CONTRASENA = "Integracion2026"
DIRECCION = {"departamento": "Valle del Cauca", "municipio": "Tuluá", "direccion": "Calle 26 # 30-15"}


@pytest.fixture
def nueva_sesion(cliente_http, correo_unico):
    """Registra un cliente nuevo e inicia sesión. Devuelve (cabeceras, id_usuario, correo)."""
    def crear():
        correo = correo_unico("rf10-15")
        registro = cliente_http.post("/api/auth/register", json={
            "nombre": "Ana", "apellido": "Pérez", "correo": correo, "contrasena": CONTRASENA})
        login = cliente_http.post("/api/auth/login", json={"correo": correo, "contrasena": CONTRASENA})
        cabeceras = {"Authorization": f"Bearer {login.get_json()['access_token']}"}
        return cabeceras, registro.get_json()["usuario"]["id_usuario"], correo
    return crear


@pytest.fixture
def sesion(nueva_sesion):
    return nueva_sesion()


@pytest.fixture
def producto_prueba(conn):
    """Producto propio (categoría propia) con dos variantes: A (stock 5) y B (stock 3).

    Al terminar se desactivan producto y categoría, para no alterar el catálogo
    que verifican otras pruebas.
    """
    sufijo = uuid.uuid4().hex[:8].upper()
    id_categoria = conn.execute("INSERT INTO categoria (nombre) VALUES (%s) RETURNING id_categoria",
                                (f"Pruebas carrito {sufijo}",)).fetchone()["id_categoria"]
    id_producto = conn.execute(
        "INSERT INTO producto (id_categoria, nombre, referencia, precio) VALUES (%s, %s, %s, %s) RETURNING id_producto",
        (id_categoria, "Producto de carrito", f"CAR-{sufijo}", Decimal("33333.33"))).fetchone()["id_producto"]
    variantes = {}
    for nombre, stock in (("A", 5), ("B", 3)):
        variantes[nombre] = conn.execute(
            "INSERT INTO variante_producto (id_producto, talla, sku, stock) VALUES (%s, %s, %s, %s) RETURNING id_variante",
            (id_producto, nombre, f"CAR-{sufijo}-{nombre}", stock)).fetchone()["id_variante"]
    yield {"id_producto": id_producto, "id_categoria": id_categoria, **variantes}
    conn.execute("UPDATE producto SET activo = false WHERE id_producto = %s", (id_producto,))
    conn.execute("UPDATE categoria SET activo = false WHERE id_categoria = %s", (id_categoria,))


def _agregar(cliente_http, cabeceras, producto, variante, cantidad):
    return cliente_http.post("/api/carrito/items", headers=cabeceras, json={
        "id_producto": producto["id_producto"], "id_variante": producto[variante], "cantidad": cantidad})


def _codigo(respuesta):
    return respuesta.get_json()["error"]["codigo"]


# ---------------------------------------------------------------------------
# RF-10 Perfil
# ---------------------------------------------------------------------------

def test_perfil_actualiza_en_la_base(cliente_http, conn, sesion):
    cabeceras, id_usuario, _ = sesion
    respuesta = cliente_http.patch("/api/perfil", headers=cabeceras,
                                   json={"apellido": "Gómez", "telefono": "+57 300 123 4567"})
    assert respuesta.status_code == 200
    fila = conn.execute("SELECT apellido, telefono, rol FROM usuario WHERE id_usuario = %s", (id_usuario,)).fetchone()
    assert fila == {"apellido": "Gómez", "telefono": "+57 300 123 4567", "rol": "cliente"}


def test_perfil_cambio_de_correo_y_login(cliente_http, sesion, correo_unico):
    cabeceras, _, _ = sesion
    nuevo = correo_unico("nuevo")
    assert cliente_http.patch("/api/perfil", headers=cabeceras, json={"correo": nuevo.upper()}).status_code == 200
    assert cliente_http.post("/api/auth/login", json={"correo": nuevo, "contrasena": CONTRASENA}).status_code == 200


def test_perfil_correo_de_otro_409(cliente_http, nueva_sesion):
    _, _, correo_otro = nueva_sesion()
    cabeceras, _, _ = nueva_sesion()
    respuesta = cliente_http.patch("/api/perfil", headers=cabeceras, json={"correo": correo_otro})
    assert respuesta.status_code == 409


def test_perfil_no_cambia_rol(cliente_http, conn, sesion):
    cabeceras, id_usuario, _ = sesion
    assert cliente_http.patch("/api/perfil", headers=cabeceras, json={"rol": "administrador"}).status_code == 400
    assert conn.execute("SELECT rol FROM usuario WHERE id_usuario = %s", (id_usuario,)).fetchone()["rol"] == "cliente"


# ---------------------------------------------------------------------------
# RF-11 Direcciones
# ---------------------------------------------------------------------------

def test_direcciones_crud_y_principal(cliente_http, conn, sesion):
    cabeceras, id_usuario, _ = sesion
    assert cliente_http.get("/api/direcciones", headers=cabeceras).get_json() == {"direcciones": []}

    primera = cliente_http.post("/api/direcciones", headers=cabeceras, json={**DIRECCION, "codigo_postal": "763021"})
    assert primera.status_code == 201
    primera = primera.get_json()["direccion"]
    assert primera["principal"] is True  # la primera queda como principal
    assert set(primera) == {"id_direccion", "departamento", "municipio", "direccion", "complemento",
                            "codigo_postal", "principal"}

    segunda = cliente_http.post("/api/direcciones", headers=cabeceras,
                                json={**DIRECCION, "direccion": "Carrera 40 # 10-20", "complemento": "Apto 301"})
    segunda = segunda.get_json()["direccion"]
    assert segunda["principal"] is False

    # Seleccionar la segunda como principal desmarca la primera.
    respuesta = cliente_http.patch(f"/api/direcciones/{segunda['id_direccion']}", headers=cabeceras,
                                   json={"principal": True, "municipio": "Buga"})
    assert respuesta.status_code == 200 and respuesta.get_json()["direccion"]["municipio"] == "Buga"
    lista = cliente_http.get("/api/direcciones", headers=cabeceras).get_json()["direcciones"]
    assert [(d["id_direccion"], d["principal"]) for d in lista] == [
        (segunda["id_direccion"], True), (primera["id_direccion"], False)]

    detalle = cliente_http.get(f"/api/direcciones/{primera['id_direccion']}", headers=cabeceras)
    assert detalle.status_code == 200 and detalle.get_json()["direccion"]["codigo_postal"] == "763021"

    # Eliminación lógica de la principal: queda inactiva y sin marca.
    assert cliente_http.delete(f"/api/direcciones/{segunda['id_direccion']}", headers=cabeceras).status_code == 204
    fila = conn.execute("SELECT activo, principal FROM direccion WHERE id_direccion = %s",
                        (segunda["id_direccion"],)).fetchone()
    assert fila == {"activo": False, "principal": False}
    lista = cliente_http.get("/api/direcciones", headers=cabeceras).get_json()["direcciones"]
    assert [d["id_direccion"] for d in lista] == [primera["id_direccion"]]
    assert cliente_http.get(f"/api/direcciones/{segunda['id_direccion']}", headers=cabeceras).status_code == 404
    assert cliente_http.delete(f"/api/direcciones/{segunda['id_direccion']}", headers=cabeceras).status_code == 404
    total = conn.execute("SELECT count(*) AS n FROM direccion WHERE id_usuario = %s", (id_usuario,)).fetchone()["n"]
    assert total == 2  # nada se borró físicamente


def test_nueva_principal_al_crear(cliente_http, sesion):
    cabeceras, _, _ = sesion
    cliente_http.post("/api/direcciones", headers=cabeceras, json=DIRECCION)
    nueva = cliente_http.post("/api/direcciones", headers=cabeceras, json={**DIRECCION, "principal": True})
    lista = cliente_http.get("/api/direcciones", headers=cabeceras).get_json()["direcciones"]
    assert [d["principal"] for d in lista].count(True) == 1
    assert lista[0]["id_direccion"] == nueva.get_json()["direccion"]["id_direccion"]


def test_direcciones_ajenas_404(cliente_http, nueva_sesion):
    cabeceras_a, _, _ = nueva_sesion()
    cabeceras_b, _, _ = nueva_sesion()
    id_direccion = cliente_http.post("/api/direcciones", headers=cabeceras_a,
                                     json=DIRECCION).get_json()["direccion"]["id_direccion"]
    ruta = f"/api/direcciones/{id_direccion}"
    assert cliente_http.get(ruta, headers=cabeceras_b).status_code == 404
    assert cliente_http.patch(ruta, headers=cabeceras_b, json={"municipio": "Cali"}).status_code == 404
    assert cliente_http.delete(ruta, headers=cabeceras_b).status_code == 404
    assert cliente_http.get("/api/direcciones", headers=cabeceras_b).get_json()["direcciones"] == []
    assert cliente_http.get(ruta, headers=cabeceras_a).get_json()["direccion"]["municipio"] == "Tuluá"


def test_editar_direccion_no_altera_pedidos(cliente_http, conn, sesion):
    cabeceras, id_usuario, _ = sesion
    direccion = cliente_http.post("/api/direcciones", headers=cabeceras, json=DIRECCION).get_json()["direccion"]
    # Pedido histórico con la copia de la dirección (como lo hará el módulo de pedidos).
    id_pedido = conn.execute(
        """INSERT INTO pedido (id_usuario, id_direccion, subtotal, total,
                               departamento_entrega, municipio_entrega, direccion_entrega)
           VALUES (%s, %s, 0, 0, %s, %s, %s) RETURNING id_pedido""",
        (id_usuario, direccion["id_direccion"], DIRECCION["departamento"], DIRECCION["municipio"],
         DIRECCION["direccion"])).fetchone()["id_pedido"]

    ruta = f"/api/direcciones/{direccion['id_direccion']}"
    assert cliente_http.patch(ruta, headers=cabeceras, json={"direccion": "Otra 1 # 2-3"}).status_code == 200
    assert cliente_http.delete(ruta, headers=cabeceras).status_code == 204
    pedido = conn.execute("SELECT id_direccion, direccion_entrega FROM pedido WHERE id_pedido = %s",
                          (id_pedido,)).fetchone()
    assert pedido == {"id_direccion": direccion["id_direccion"], "direccion_entrega": DIRECCION["direccion"]}


# ---------------------------------------------------------------------------
# RF-12 a RF-15 Carrito
# ---------------------------------------------------------------------------

def test_carrito_vacio_sin_crear_fila(cliente_http, conn, sesion):
    cabeceras, id_usuario, _ = sesion
    carrito = cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]
    assert carrito["id_carrito"] is None and carrito["vacio"] is True and carrito["total"] == "0.00"
    assert conn.execute("SELECT count(*) AS n FROM carrito WHERE id_usuario = %s", (id_usuario,)).fetchone()["n"] == 0


def test_flujo_completo_del_carrito(cliente_http, conn, sesion, producto_prueba):
    cabeceras, id_usuario, _ = sesion
    respuesta = _agregar(cliente_http, cabeceras, producto_prueba, "A", 2)
    assert respuesta.status_code == 200
    carrito = respuesta.get_json()["carrito"]
    item = carrito["items"][0]
    assert (item["cantidad"], item["precio_unitario"], item["subtotal"]) == (2, "33333.33", "66666.66")
    assert (item["talla"], item["disponible"], item["stock_disponible"]) == ("A", True, 5)
    assert carrito["total"] == "66666.66"

    # Agregar de nuevo la misma variante incrementa la línea (no la duplica).
    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "A", 1).get_json()["carrito"]
    assert [(i["id_variante"], i["cantidad"]) for i in carrito["items"]] == [(producto_prueba["A"], 3)]

    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "B", 1).get_json()["carrito"]
    assert carrito["total"] == "133333.32" and carrito["cantidad_unidades"] == 4
    id_linea_a = carrito["items"][0]["id_detalle_carrito"]
    id_linea_b = carrito["items"][1]["id_detalle_carrito"]

    # RF-13 modificar cantidad.
    carrito = cliente_http.patch(f"/api/carrito/items/{id_linea_a}", headers=cabeceras,
                                 json={"cantidad": 5}).get_json()["carrito"]
    assert carrito["items"][0]["cantidad"] == 5 and carrito["total"] == "199999.98"

    # GET devuelve lo mismo.
    assert cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"] == carrito

    # RF-14 retirar (borrado lógico) y reactivar.
    carrito = cliente_http.delete(f"/api/carrito/items/{id_linea_b}", headers=cabeceras).get_json()["carrito"]
    assert [i["id_detalle_carrito"] for i in carrito["items"]] == [id_linea_a]
    assert conn.execute("SELECT activo FROM detalle_carrito WHERE id_detalle_carrito = %s",
                        (id_linea_b,)).fetchone()["activo"] is False
    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "B", 2).get_json()["carrito"]
    linea_b = next(i for i in carrito["items"] if i["id_variante"] == producto_prueba["B"])
    assert (linea_b["id_detalle_carrito"], linea_b["cantidad"]) == (id_linea_b, 2)  # misma fila reactivada

    # Retirar todo deja el carrito vacío (pero existente).
    for item in carrito["items"]:
        carrito = cliente_http.delete(f"/api/carrito/items/{item['id_detalle_carrito']}",
                                      headers=cabeceras).get_json()["carrito"]
    assert carrito["vacio"] is True and carrito["total"] == "0.00" and carrito["id_carrito"] is not None

    carritos = conn.execute("SELECT count(*) AS n FROM carrito WHERE id_usuario = %s AND estado = 'abierto'",
                            (id_usuario,)).fetchone()["n"]
    assert carritos == 1


def test_carrito_no_modifica_inventario(cliente_http, conn, sesion, producto_prueba):
    cabeceras, _, _ = sesion

    def estado():
        stock = conn.execute("SELECT sum(stock) AS s FROM variante_producto WHERE id_producto = %s",
                             (producto_prueba["id_producto"],)).fetchone()["s"]
        movimientos = conn.execute("SELECT count(*) AS n FROM movimiento_inventario").fetchone()["n"]
        pedidos = conn.execute("SELECT count(*) AS n FROM pedido").fetchone()["n"]
        return stock, movimientos, pedidos

    antes = estado()
    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "A", 5).get_json()["carrito"]
    cliente_http.patch(f"/api/carrito/items/{carrito['items'][0]['id_detalle_carrito']}",
                       headers=cabeceras, json={"cantidad": 4})
    assert estado() == antes


def test_stock_insuficiente(cliente_http, sesion, producto_prueba):
    cabeceras, _, _ = sesion
    respuesta = _agregar(cliente_http, cabeceras, producto_prueba, "B", 4)
    assert respuesta.status_code == 409 and _codigo(respuesta) == "stock_insuficiente"
    assert respuesta.get_json()["error"]["detalles"] == {"stock_disponible": 3, "cantidad_en_carrito": 0}

    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "B", 2).get_json()["carrito"]
    respuesta = _agregar(cliente_http, cabeceras, producto_prueba, "B", 2)  # 2 + 2 > 3
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"]["detalles"]["cantidad_en_carrito"] == 2

    id_linea = carrito["items"][0]["id_detalle_carrito"]
    respuesta = cliente_http.patch(f"/api/carrito/items/{id_linea}", headers=cabeceras, json={"cantidad": 4})
    assert respuesta.status_code == 409 and _codigo(respuesta) == "stock_insuficiente"
    assert cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]["items"][0]["cantidad"] == 2


def test_variante_de_otro_producto_e_inexistente(cliente_http, conn, sesion, producto_prueba):
    cabeceras, _, _ = sesion
    ajena = conn.execute("SELECT id_variante FROM variante_producto WHERE sku = 'CAS-INT-001-M-NEG'").fetchone()
    respuesta = cliente_http.post("/api/carrito/items", headers=cabeceras, json={
        "id_producto": producto_prueba["id_producto"], "id_variante": ajena["id_variante"], "cantidad": 1})
    assert respuesta.status_code == 400 and "id_variante" in respuesta.get_json()["error"]["detalles"]["campos"]

    respuesta = cliente_http.post("/api/carrito/items", headers=cabeceras, json={
        "id_producto": producto_prueba["id_producto"], "id_variante": 2_147_483_647, "cantidad": 1})
    assert respuesta.status_code == 404 and _codigo(respuesta) == "variante_no_encontrada"


@pytest.mark.parametrize("sku", ["CAS-ABA-002-XL-BLA", "CHA-CUE-002-M-CAF", "REP-PAS-001-URB150"])
def test_no_se_agregan_variantes_productos_o_categorias_inactivos(cliente_http, conn, sesion, sku):
    cabeceras, _, _ = sesion
    variante = conn.execute("SELECT id_variante, id_producto FROM variante_producto WHERE sku = %s", (sku,)).fetchone()
    respuesta = cliente_http.post("/api/carrito/items", headers=cabeceras, json={**variante, "cantidad": 1})
    assert respuesta.status_code == 409 and _codigo(respuesta) == "producto_no_disponible"


def test_variante_base_se_agrega(cliente_http, conn, sesion):
    cabeceras, _, _ = sesion
    variante = conn.execute("SELECT id_variante, id_producto FROM variante_producto WHERE sku = 'ACC-SOP-001'").fetchone()
    carrito = cliente_http.post("/api/carrito/items", headers=cabeceras,
                                json={**variante, "cantidad": 1}).get_json()["carrito"]
    item = carrito["items"][0]
    assert (item["talla"], item["color"], item["compatibilidad"], item["precio_unitario"]) == (None, None, None, "65000.00")


def test_articulo_que_queda_no_disponible_se_muestra_y_se_retira(cliente_http, conn, sesion, producto_prueba):
    cabeceras, _, _ = sesion
    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "A", 2).get_json()["carrito"]
    id_linea = carrito["items"][0]["id_detalle_carrito"]

    conn.execute("UPDATE variante_producto SET stock = 1 WHERE id_variante = %s", (producto_prueba["A"],))
    item = cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]["items"][0]
    assert (item["disponible"], item["motivo_no_disponible"]) == (False, "stock_insuficiente")

    conn.execute("UPDATE producto SET activo = false WHERE id_producto = %s", (producto_prueba["id_producto"],))
    carrito = cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]
    assert carrito["items"][0]["motivo_no_disponible"] == "producto_inactivo"
    assert carrito["todos_disponibles"] is False

    respuesta = cliente_http.patch(f"/api/carrito/items/{id_linea}", headers=cabeceras, json={"cantidad": 1})
    assert respuesta.status_code == 409 and _codigo(respuesta) == "producto_no_disponible"
    carrito = cliente_http.delete(f"/api/carrito/items/{id_linea}", headers=cabeceras).get_json()["carrito"]
    assert carrito["vacio"] is True


def test_carrito_ajeno_404(cliente_http, nueva_sesion, producto_prueba):
    cabeceras_a, _, _ = nueva_sesion()
    cabeceras_b, _, _ = nueva_sesion()
    carrito = _agregar(cliente_http, cabeceras_a, producto_prueba, "A", 1).get_json()["carrito"]
    id_linea = carrito["items"][0]["id_detalle_carrito"]
    ruta = f"/api/carrito/items/{id_linea}"
    assert cliente_http.patch(ruta, headers=cabeceras_b, json={"cantidad": 2}).status_code == 404
    assert cliente_http.delete(ruta, headers=cabeceras_b).status_code == 404
    assert cliente_http.get("/api/carrito", headers=cabeceras_b).get_json()["carrito"]["vacio"] is True
    assert cliente_http.get("/api/carrito", headers=cabeceras_a).get_json()["carrito"]["items"][0]["cantidad"] == 1


@pytest.mark.parametrize("estado", ["convertido", "abandonado"])
def test_carrito_convertido_o_abandonado_no_se_modifica(cliente_http, conn, sesion, producto_prueba, estado):
    cabeceras, _, _ = sesion
    carrito = _agregar(cliente_http, cabeceras, producto_prueba, "A", 1).get_json()["carrito"]
    id_linea = carrito["items"][0]["id_detalle_carrito"]
    conn.execute("UPDATE carrito SET estado = %s WHERE id_carrito = %s", (estado, carrito["id_carrito"]))

    ruta = f"/api/carrito/items/{id_linea}"
    respuesta = cliente_http.patch(ruta, headers=cabeceras, json={"cantidad": 2})
    assert respuesta.status_code == 409 and _codigo(respuesta) == "carrito_no_modificable"
    assert cliente_http.delete(ruta, headers=cabeceras).status_code == 409
    assert conn.execute("SELECT cantidad, activo FROM detalle_carrito WHERE id_detalle_carrito = %s",
                        (id_linea,)).fetchone() == {"cantidad": 1, "activo": True}

    # El usuario no tiene carrito abierto: GET vacío y el siguiente artículo crea uno nuevo.
    assert cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]["id_carrito"] is None
    nuevo = _agregar(cliente_http, cabeceras, producto_prueba, "A", 1).get_json()["carrito"]
    assert nuevo["id_carrito"] != carrito["id_carrito"]


def test_administrador_usa_su_propio_carrito(app_bd, cliente_http, conn, correo_unico, producto_prueba):
    correo = correo_unico("admin-carrito")
    app_bd.test_cli_runner().invoke(args=["crear-admin"],
                                    input=f"Ad\nMin\n{correo}\n\n{CONTRASENA}\n{CONTRASENA}\n")
    token = cliente_http.post("/api/auth/login", json={"correo": correo, "contrasena": CONTRASENA}).get_json()
    cabeceras = {"Authorization": f"Bearer {token['access_token']}"}
    assert cliente_http.get("/api/carrito", headers=cabeceras).get_json()["carrito"]["vacio"] is True
    assert _agregar(cliente_http, cabeceras, producto_prueba, "A", 1).status_code == 200
    assert cliente_http.post("/api/direcciones", headers=cabeceras, json=DIRECCION).status_code == 201
