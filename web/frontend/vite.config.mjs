import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/static/dashboard/",
  optimizeDeps: {
    include: ["react", "react-dom/client", "echarts/core"],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5000",
    },
    warmup: {
      clientFiles: ["./src/main.jsx"],
    },
  },
  build: {
    outDir: "../static/dashboard",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalized = id.replaceAll("\\", "/");
          if (normalized.includes("/node_modules/zrender/")) return "vendor-zrender";
          if (normalized.includes("/node_modules/echarts/")) return "vendor-echarts";
          if (normalized.includes("/node_modules/@ant-design/icons")) return "vendor-icons";
          if (normalized.includes("/node_modules/react")) return "vendor-react";
          return undefined;
        },
      },
    },
  },
  plugins: [react()],
});
