import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";

import { ApiError, registrarManejadorSesion, solicitar, token } from "../api/client";
import { describirVariante, formatoCOP, formatoFecha } from "../utils/format";
import * as v from "../utils/validacion";
import { tieneRol, puedeComprar } from "../utils/roles";
import { API, error, servidor } from "./servidor";

describe("formatos", () => {
  it("muestra pesos colombianos sin decimales", () => {
    expect(formatoCOP("450000.00").replace(/\s/g, " ")).toBe("$ 450.000");
  });
  it("muestra las fechas en hora de Colombia", () => {
    expect(formatoFecha("2026-11-26T15:30:00+00:00")).toMatch(/26 de noviembre de 2026.*10:30/);
  });
  it("describe variantes y la variante base", () => {
    expect(describirVariante({ talla: "M", color: "Negro mate", compatibilidad: null })).toBe("M / Negro mate");
    expect(describirVariante({ talla: null, color: null, compatibilidad: null })).toBe("Única");
  });
});

describe("validación igual a la del backend", () => {
  it("contraseña: 8-128, letra y número", () => {
    expect(v.contrasena("corta1")).toMatch(/entre 8 y 128/);
    expect(v.contrasena("soloLetras")).toMatch(/letra y un número/);
    expect(v.contrasena("Segura2026")).toBeNull();
  });
  it("correo y teléfono", () => {
    expect(v.correo("ana@ejemplo")).toMatch(/formato/);
    expect(v.correo(" Ana@Ejemplo.com ")).toBeNull();
    expect(v.telefono("+57 300 123 4567")).toBeNull();
    expect(v.telefono("abc")).toMatch(/solo admite/);
    expect(v.telefono("")).toBeNull();
  });
  it("código postal de 4 a 10 dígitos", () => {
    expect(v.codigoPostal("763021")).toBeNull();
    expect(v.codigoPostal("76A")).toMatch(/4 y 10/);
  });
});

describe("roles", () => {
  it("el administrador supera cualquier rol; el empleado no compra", () => {
    expect(tieneRol({ rol: "administrador" }, "cliente")).toBe(true);
    expect(puedeComprar({ rol: "empleado" })).toBe(false);
    expect(puedeComprar({ rol: "cliente" })).toBe(true);
  });
});

describe("cliente HTTP", () => {
  it("envía el token como Bearer", async () => {
    token.guardar("abc.def");
    let cabecera;
    servidor.use(
      http.get(`${API}/auth/me`, ({ request }) => {
        cabecera = request.headers.get("Authorization");
        return HttpResponse.json({ usuario: {} });
      })
    );
    await solicitar("/auth/me");
    expect(cabecera).toBe("Bearer abc.def");
  });

  it("convierte el formato de error de la API en ApiError con campos", async () => {
    servidor.use(
      http.post(`${API}/auth/register`, () =>
        error(400, "validacion", "Revise los datos ingresados.", { campos: { correo: "El correo electrónico no tiene un formato válido." } })
      )
    );
    const e = await solicitar("/auth/register", { metodo: "POST", cuerpo: {} }).catch((x) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect(e.codigo).toBe("validacion");
    expect(e.campos.correo).toMatch(/formato/);
  });

  it("ante 401 en ruta protegida borra el token y avisa la pérdida de sesión", async () => {
    token.guardar("vencido");
    const manejador = vi.fn();
    registrarManejadorSesion(manejador);
    servidor.use(http.get(`${API}/carrito`, () => error(401, "token_expirado", "Su sesión expiró.")));
    await expect(solicitar("/carrito")).rejects.toMatchObject({ codigo: "token_expirado" });
    expect(token.obtener()).toBeNull();
    expect(manejador).toHaveBeenCalledOnce();
  });

  it("un 401 del login no cierra la sesión ni redirige", async () => {
    const manejador = vi.fn();
    registrarManejadorSesion(manejador);
    servidor.use(http.post(`${API}/auth/login`, () => error(401, "credenciales_invalidas", "Correo electrónico o contraseña incorrectos.")));
    await expect(solicitar("/auth/login", { metodo: "POST", cuerpo: {} })).rejects.toMatchObject({ status: 401 });
    expect(manejador).not.toHaveBeenCalled();
  });

  it("un 403 no borra el token", async () => {
    token.guardar("valido");
    servidor.use(http.get(`${API}/carrito`, () => error(403, "acceso_denegado", "No tiene permisos para realizar esta acción.")));
    await expect(solicitar("/carrito")).rejects.toMatchObject({ status: 403 });
    expect(token.obtener()).toBe("valido");
  });

  it("informa la falta de conexión", async () => {
    servidor.use(http.get(`${API}/health`, () => HttpResponse.error()));
    await expect(solicitar("/health")).rejects.toMatchObject({ codigo: "sin_conexion" });
  });

  it("lee Retry-After del 429", async () => {
    servidor.use(
      http.post(`${API}/auth/login`, () =>
        HttpResponse.json({ error: { codigo: "demasiadas_solicitudes", mensaje: "Demasiados intentos." } }, { status: 429, headers: { "Retry-After": "120" } })
      )
    );
    const e = await solicitar("/auth/login", { metodo: "POST", cuerpo: {} }).catch((x) => x);
    expect(e.retryAfter).toBe(120);
  });
});
