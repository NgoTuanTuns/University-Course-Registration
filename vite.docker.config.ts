import { mergeConfig } from "vite";
import baseConfig from "./vite.config";

export default mergeConfig(baseConfig, {
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true,
      interval: 1000,
      ignored: [
        "**/.git/**",
        "**/.venv/**",
        "**/backend/**",
        "**/docker/**",
        "**/docs/**",
        "**/node_modules/**",
        "**/.pytest_cache/**",
        "**/.ruff_cache/**",
        "**/dist/**",
        "**/chitietcongviec/**",
        "**/ban_giao/**",
      ],
    },
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL || "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});
