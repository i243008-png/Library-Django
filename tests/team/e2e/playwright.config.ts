import { defineConfig, devices } from '@playwright/test';

// The app shows times in Europe/Kyiv (TIME_ZONE in settings.py), so the browser uses it too.
// Two projects: `e2e` (use case flows, `npm test`) and `a11y` (axe scans and reflow checks, `npm run a11y`).
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.BASE_URL ?? 'http://localhost:8000',
    locale: 'en-US',
    timezoneId: 'Europe/Kyiv',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'e2e', testMatch: /uc\d+-.*\.spec\.ts/ },
    { name: 'a11y', testMatch: /(a11y|reflow)\.spec\.ts/ },
  ],
});