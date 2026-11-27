import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { renderApp, ubicacionActual } from "./renderApp";
import { token } from "../api/client";
import { API, carritoCon, cliente, direcciones, empleado, error, manejadoresBase, servidor } from "./servidor";

describe("autenticación", () => {
  it("sin sesión, cualquier ruta protegida lleva al login", async () => {
    renderApp("/productos", { sesion: false });
    expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
  });

  it("inicia sesión, guarda el token y vuelve a la página pedida", async () => {
    servidor.use(
      http.post(`${API}/auth/login`, async ({ request }) => {
        const cuerpo = await request.json();
        expect(cuerpo).toEqual({ correo: "ana@ejemplo.com", contrasena: "Segura2026" });
        return HttpResponse.json({ access_token: "jwt-nuevo", token_type: "Bearer", expires_in: 3600, usuario: cliente });
      }),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/productos", { sesion: false });
    await u.type(await screen.findByLabelText(/Correo electrónico/), "ana@ejemplo.com");
    await u.type(screen.getByLabelText(/^Contraseña/), "Segura2026");
    await u.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    expect(await screen.findByRole("heading", { name: "Catálogo" })).toBeInTheDocument();
    expect(token.obtener()).toBe("jwt-nuevo");
  });

  it("muestra el error de credenciales sin salir del login", async () => {
    servidor.use(http.post(`${API}/auth/login`, () => error(401, "credenciales_invalidas", "Correo electrónico o contraseña incorrectos.")));
    const u = userEvent.setup();
    renderApp("/login", { sesion: false });
    await u.type(screen.getByLabelText(/Correo electrónico/), "ana@ejemplo.com");
    await u.type(screen.getByLabelText(/^Contraseña/), "Mala1234");
    await u.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Correo electrónico o contraseña incorrectos.");
    expect(ubicacionActual.pathname).toBe("/login");
  });

  it("valida el formulario antes de enviar", async () => {
    const u = userEvent.setup();
    renderApp("/login", { sesion: false });
    await u.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    expect(await screen.findByText("El correo electrónico es obligatorio.")).toBeInTheDocument();
  });

  it("si el token expiró, vuelve al login con aviso", async () => {
    servidor.use(http.get(`${API}/auth/me`, () => error(401, "token_expirado", "Su sesión expiró.")));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
    expect(token.obtener()).toBeNull();
  });

  it("registro: muestra en el campo un correo ya registrado", async () => {
    servidor.use(http.post(`${API}/auth/register`, () => error(409, "correo_ya_registrado", "Ya existe una cuenta registrada con ese correo electrónico.")));
    const u = userEvent.setup();
    renderApp("/registro", { sesion: false });
    await u.type(await screen.findByLabelText(/^Nombre/), "Ana");
    await u.type(screen.getByLabelText(/^Apellido/), "Pérez");
    await u.type(screen.getByLabelText(/Correo electrónico/), "ana@ejemplo.com");
    await u.type(screen.getByLabelText(/^Contraseña/), "Segura2026");
    await u.type(screen.getByLabelText(/Confirmar contraseña/), "Segura2026");
    await u.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByText("Ya existe una cuenta registrada con ese correo electrónico.")).toBeInTheDocument();
  });
});

describe("catálogo y carrito", () => {
  it("busca y envía el parámetro a la API", async () => {
    const consultas = [];
    servidor.use(
      http.get(`${API}/productos`, ({ request }) => {
        consultas.push(new URL(request.url).searchParams.get("busqueda"));
        return HttpResponse.json({ productos: [], total_resultados: 0, pagina: 1, por_pagina: 12, total_paginas: 0 });
      }),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/productos");
    await u.type(await screen.findByRole("searchbox"), "casco");
    expect(await screen.findByText("No se encontraron productos")).toBeInTheDocument();
    await waitFor(() => expect(consultas).toContain("casco"));
  });

  it("agrega la variante elegida al carrito y actualiza el contador", async () => {
    let cuerpo;
    servidor.use(
      http.post(`${API}/carrito/items`, async ({ request }) => {
        cuerpo = await request.json();
        return HttpResponse.json({ carrito: carritoCon(2) });
      }),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/productos/2");
    expect(await screen.findByRole("heading", { name: "Casco abatible Urbano Pro" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /XL \/ Blanco/ })).toBeDisabled();
    await u.click(screen.getByRole("radio", { name: "L / Blanco" }));
    await u.click(screen.getByRole("button", { name: "Aumentar cantidad" }));
    expect(screen.getByRole("button", { name: "Aumentar cantidad" })).toBeDisabled(); // stock 2
    await u.click(screen.getByRole("button", { name: "Agregar al carrito" }));
    await waitFor(() => expect(cuerpo).toEqual({ id_producto: 2, id_variante: 5, cantidad: 2 }));
    expect(await screen.findByRole("button", { name: "Abrir carrito, 2 unidades" })).toBeInTheDocument();
  });

  it("explica el stock insuficiente al agregar", async () => {
    servidor.use(
      http.post(`${API}/carrito/items`, () =>
        error(409, "stock_insuficiente", "No hay unidades suficientes.", { stock_disponible: 3, cantidad_en_carrito: 3 })
      ),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/productos/2");
    await u.click(await screen.findByRole("button", { name: "Agregar al carrito" }));
    expect(await screen.findByText("Ya tienes 3 en el carrito y solo hay 3 disponibles.")).toBeInTheDocument();
  });

  it("marca un artículo sin stock suficiente y permite ajustarlo", async () => {
    let patch;
    servidor.use(
      http.get(`${API}/carrito`, () =>
        HttpResponse.json({ carrito: carritoCon(4, { disponible: false, motivo_no_disponible: "stock_insuficiente", stock_disponible: 2 }) })
      ),
      http.patch(`${API}/carrito/items/88`, async ({ request }) => {
        patch = await request.json();
        return HttpResponse.json({ carrito: carritoCon(2) });
      }),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/carrito");
    expect(await screen.findByText(/No hay unidades suficientes/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Continuar con el pedido" })[0]).toBeDisabled();
    await u.click(screen.getByRole("button", { name: "Ajustar a 2" }));
    await waitFor(() => expect(patch).toEqual({ cantidad: 2 }));
    expect(await screen.findByRole("link", { name: "Continuar con el pedido" })).toBeInTheDocument();
  });

  it("el empleado consulta existencias pero no ve el carrito", async () => {
    servidor.use(...manejadoresBase(empleado));
    renderApp("/productos/2");
    expect(await screen.findByText("Vista de consulta")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar al carrito" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Abrir carrito/ })).not.toBeInTheDocument();
  });

  it("el empleado no entra al carrito", async () => {
    servidor.use(...manejadoresBase(empleado));
    renderApp("/carrito");
    expect(await screen.findByText("Esta sección no está disponible para tu rol")).toBeInTheDocument();
  });
});

describe("pedido", () => {
  it("confirma con la dirección principal y muestra el pedido registrado", async () => {
    let cuerpo;
    servidor.use(
      http.get(`${API}/carrito`, () => HttpResponse.json({ carrito: carritoCon(1) })),
      http.post(`${API}/pedidos`, async ({ request }) => {
        cuerpo = await request.json();
        return HttpResponse.json(
          {
            pedido: {
              id_pedido: 15, fecha: "2026-11-26T15:30:00+00:00", estado: "pendiente", fecha_actualizacion: "2026-11-26T15:30:00+00:00",
              entrega: { id_direccion: 12, ...direcciones[0] }, observaciones: "Llamar antes",
              detalles: [{ id_detalle: 31, id_producto: 2, id_variante: 5, nombre: "Casco abatible Urbano Pro", referencia: "CAS-ABA-002", imagen: null, sku: "CAS-ABA-002-L-BLA", talla: "L", color: "Blanco", compatibilidad: null, cantidad: 1, precio_unitario: "380000.00", subtotal: "380000.00" }],
              cantidad_unidades: 1, subtotal: "380000.00", total: "380000.00",
            },
          },
          { status: 201 }
        );
      }),
      ...manejadoresBase()
    );
    const u = userEvent.setup();
    renderApp("/pedido");
    const principal = await screen.findByRole("radio", { name: /Calle 26 # 30-15/ });
    expect(principal).toHaveAttribute("aria-checked", "true");
    await u.type(screen.getByLabelText(/Observaciones/), "Llamar antes");
    await u.click(screen.getByRole("button", { name: "Revisar pedido" }));
    await u.click(await screen.findByRole("button", { name: /Confirmar pedido por/ }));
    await waitFor(() => expect(cuerpo).toEqual({ id_direccion: 12, observaciones: "Llamar antes" }));
    expect(await screen.findByRole("heading", { name: /Registramos tu pedido #15/ })).toBeInTheDocument();
    expect(ubicacionActual.pathname).toBe("/pedidos/15");
    expect(screen.getByText("Pendiente").closest("li")).toHaveAttribute("aria-current", "step");
  });

  it("si cambió la disponibilidad al confirmar, vuelve al carrito", async () => {
    servidor.use(
      http.get(`${API}/carrito`, () => HttpResponse.json({ carrito: carritoCon(1) })),
      http.post(`${API}/pedidos`, () => error(409, "articulos_no_disponibles", "Algunos artículos no están disponibles.", { items: [] })),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/pedido");
    await u.click(await screen.findByRole("button", { name: "Revisar pedido" }));
    await u.click(await screen.findByRole("button", { name: /Confirmar pedido por/ }));
    await waitFor(() => expect(ubicacionActual.pathname).toBe("/carrito"));
  });

  it("pedido ajeno o inexistente", async () => {
    servidor.use(http.get(`${API}/pedidos/99`, () => error(404, "pedido_no_encontrado", "El pedido no existe.")), ...manejadoresBase());
    renderApp("/pedidos/99");
    expect(await screen.findByText("No encontramos este pedido")).toBeInTheDocument();
  });
});

describe("cuenta", () => {
  it("envía solo los campos modificados del perfil", async () => {
    let cuerpo;
    servidor.use(
      http.patch(`${API}/perfil`, async ({ request }) => {
        cuerpo = await request.json();
        return HttpResponse.json({ usuario: { ...cliente, telefono: "3001234567" } });
      }),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/cuenta");
    const telefono = await screen.findByLabelText(/^Teléfono/);
    await u.type(telefono, "3001234567");
    await u.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(cuerpo).toEqual({ telefono: "3001234567" }));
    expect(await screen.findByText("Datos guardados.")).toBeInTheDocument();
  });

  it("marca otra dirección como principal", async () => {
    let cuerpo;
    servidor.use(
      http.patch(`${API}/direcciones/13`, async ({ request }) => {
        cuerpo = await request.json();
        return HttpResponse.json({ direccion: { ...direcciones[1], principal: true } });
      }),
      ...manejadoresBase()
    )
    const u = userEvent.setup();
    renderApp("/cuenta");
    await u.click(await screen.findByRole("button", { name: "Usar como principal" }));
    await waitFor(() => expect(cuerpo).toEqual({ principal: true }));
  });
});
