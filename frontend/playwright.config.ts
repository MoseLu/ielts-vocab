import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:3020'
const shouldStartLocalFrontend =
  !process.env.BASE_URL &&
  process.env.PLAYWRIGHT_SKIP_WEBSERVER !== 'true'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  webServer: shouldStartLocalFrontend
    ? {
        command: 'pnpm dev -- --host 127.0.0.1 --port 3020',
        cwd: '.',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      }
    : undefined,
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
