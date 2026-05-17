import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: 'src/tests/e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: 'list',
	webServer: {
		// Re-use the existing build/ directory — callers are expected to run
		// `pnpm build` with the right env (VITE_BUILD_SHA etc.) themselves.
		// This avoids re-running the build in a subshell that has lost env vars.
		command: 'pnpm preview --port 4173 --host 127.0.0.1',
		port: 4173,
		reuseExistingServer: !process.env.CI
	},
	use: {
		baseURL: 'http://127.0.0.1:4173',
		trace: 'on-first-retry'
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		},
		{
			name: 'mobile',
			use: {
				...devices['Pixel 5'],
				viewport: { width: 360, height: 640 }
			}
		}
	]
});
