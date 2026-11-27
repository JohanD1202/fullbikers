import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup, configure } from "@testing-library/react";

import { servidor } from "./servidor";

// Las rutas se cargan con lazy(): la primera importación puede tardar más de 1 s.
configure({ asyncUtilTimeout: 5000 });

// jsdom no implementa estas API del navegador.
window.scrollTo = vi.fn();
window.matchMedia =
  window.matchMedia ||
  ((query) => ({
    matches: query.includes("reduce"),
    media: query,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
    onchange: null,
    dispatchEvent: () => false,
  }));
if (!window.IntersectionObserver) {
  window.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

beforeAll(() => servidor.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  servidor.resetHandlers();
  sessionStorage.clear();
});
afterAll(() => servidor.close());
