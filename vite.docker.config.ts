import { mergeConfig } from "vite";
import baseConfig from "./vite.config";

export default mergeConfig(baseConfig, {
  server: {
    watch: {
      usePolling: true,
    },
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL || "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});
