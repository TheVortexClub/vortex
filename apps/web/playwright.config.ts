import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

// End-to-end tests run their own API (simulated model, accounts on) and web server,
// so they never touch your real data or model.
const API_PORT = 8101;
const WEB_PORT = 3101;
const tmp = path.join(os.tmpdir(), `vortex-e2e-${Date.now()}`);
const python = process.env.PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    // Uses an installed browser (Edge on Windows, Chrome elsewhere); no download needed.
    channel: process.env.PW_CHANNEL ?? (process.platform === "win32" ? "msedge" : "chrome"),
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `${python} -m uvicorn vortex_api.main:create_app --factory --host 127.0.0.1 --port ${API_PORT}`,
      cwd: "../api",
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: false,
      env: {
        VORTEX_MOCK_BACKEND: "true",
        VORTEX_LOCAL_MODE: "false",
        VORTEX_DB_AUTO_CREATE: "true",
        VORTEX_DATABASE_URL: `sqlite+aiosqlite:///${path.join(tmp, "e2e.db").replace(/\\/g, "/")}`,
        VORTEX_DATA_DIR: tmp,
        VORTEX_RATE_LIMIT_PER_MINUTE: "0",
      },
    },
    {
      command: "node server.mjs",
      url: `http://127.0.0.1:${WEB_PORT}/login`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        API_INTERNAL_URL: `http://127.0.0.1:${API_PORT}`,
        PORT: String(WEB_PORT),
        NEXT_DIST_DIR: ".next-e2e",
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
