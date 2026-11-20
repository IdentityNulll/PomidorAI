import { defineConfig, devices } from '@playwright/test';

// The iPhone 13 profile normally drives WebKit, but Playwright's WebKit build
// needs system packages this machine does not have (libevent-2.1-7t64,
// libmanette-0.2-0 - installable with `sudo npx playwright install-deps`).
// Until those are installed both profiles run on Chromium, which still applies
// each device's viewport, device-pixel-ratio, touch support and user agent.
const iPhone13 = { ...devices['iPhone 13'], defaultBrowserType: 'chromium' as const };

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.POMIDORAI_URL ?? 'http://127.0.0.1:8000',
    trace: 'off',
  },
  projects: [
    { name: 'iPhone 13', use: iPhone13 },
    { name: 'Pixel 7', use: { ...devices['Pixel 7'] } },
  ],
});
