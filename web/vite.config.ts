import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// 构建产物放进服务端包里（随仓库提交）：用户本地运行只要 Python，不需要 Node。
const outDir = fileURLToPath(new URL("../server/teamflow_server/web_dist", import.meta.url));

// 开发时（npm run dev）把接口转给本机的服务端。不加 X-Forwarded-*：服务端看到转发头会当成不是本机来的，返回 404。
const backend = process.env.TEAMFLOW_WEB_BACKEND ?? "http://127.0.0.1:8100";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir,
    emptyOutDir: true,
    assetsInlineLimit: 0, // CSP 是 img-src 'self' data:，但字体、脚本都不许内联；统一出文件
    sourcemap: false,
    chunkSizeWarningLimit: 400,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: backend, changeOrigin: false, xfwd: false },
      "/dev": { target: backend, changeOrigin: false, xfwd: false },
    },
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/setup.ts"],
    restoreMocks: true,
  },
});
