import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:18765",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:18765",
        ws: true,
      },
    },
  },
});
