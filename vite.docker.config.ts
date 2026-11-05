import { mergeConfig } from "vite";
import baseConfig from "./vite.config";

export default mergeConfig(baseConfig, {
  server: {
    watch: {
      usePolling: true,
    },
  },
});
