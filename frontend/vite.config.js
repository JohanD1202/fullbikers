import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Puerto 5173: es el origen que el backend admite por CORS en desarrollo
// (CORS_ORIGINS=http://localhost:5173 en backend/.env).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, host: "localhost" },
  test: {
    environment: "jsdom",
    globals: true,
    testTimeout: 20000,
    setupFiles: ["./src/test/setup.js"],
    css: { modules: { classNameStrategy: "non-scoped" } },
  },
});
