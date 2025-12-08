import { defineConfig } from "vitest/config";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["../test/web/setupTests.ts"],
    include: ["../test/web/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      reportsDirectory: "../test/web/coverage"
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname)
    }
  },
  esbuild: {
    jsx: "automatic"
  },
  define: {
    "process.env.NEXT_PUBLIC_API_BASE_URL": JSON.stringify("http://localhost:8000")
  }
});