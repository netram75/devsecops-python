import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production nginx (compose) or the Ingress (k8s) routes /api to the backend.
// For `npm run dev` Vite proxies it to a backend on localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: { sourcemap: false },
});
