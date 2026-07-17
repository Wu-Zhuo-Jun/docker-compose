import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import viteCompression from "vite-plugin-compression";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [
          [
            "babel-plugin-import",
            {
              libraryName: "antd",
              libraryDirectory: "es",
              style: false,
            },
          ],
        ],
      },
    }),
    // 生成 gzip 压缩文件
    viteCompression({
      algorithm: "gzip",
      ext: ".gz",
      threshold: 1024, // 只压缩大于 1KB 的文件
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 8002,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    // 使用 esbuild 压缩 (默认)
    minify: "esbuild",
    // 启用代码分割
    rollupOptions: {
      output: {
        // 大库分包
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          antd: ["antd"],
        },
      },
    },
    // 移除 console 和 debugger
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    // 关闭 sourcemap (生产环境不需要)
    sourcemap: false,
  },
});
