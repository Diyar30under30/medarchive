import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend dev server on :5173. The API base is injected via VITE_API_BASE
// (defaults to localhost:8000) so the same build works in Docker and on host.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
