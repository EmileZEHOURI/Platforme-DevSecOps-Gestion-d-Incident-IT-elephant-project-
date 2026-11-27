import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 60000,
  expect: { timeout: 15000 },
  use: {
    baseURL: "http://127.0.0.1:3017",
    browserName: "chromium",
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3017",
    url: "http://127.0.0.1:3017/login",
    reuseExistingServer: false,
    timeout: 120000,
    env: {
      E2E_TEST: "1",
      API_URL: "http://127.0.0.1:8017",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
});
