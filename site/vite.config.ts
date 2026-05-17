import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	test: {
		include: ['src/tests/unit/**/*.{test,spec}.{js,ts}'],
		environment: 'jsdom',
		environmentOptions: {
			jsdom: {
				url: 'http://localhost/'
			}
		},
		setupFiles: ['./src/tests/setup.ts'],
		globals: false
	}
});
