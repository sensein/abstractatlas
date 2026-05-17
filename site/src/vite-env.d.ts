/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_BUILD_SHA?: string;
	readonly VITE_BUILD_SHA_SHORT?: string;
	readonly VITE_BUILD_AT?: string;
	/**
	 * Public URL of the data-package tarball (Dropbox / S3 / etc.).
	 * The client fetches + decompresses + untars in-browser on first paint.
	 * Set at build time from the OHBM2026_UI_DATA_PACKAGE_URL repo variable.
	 */
	readonly VITE_DATA_PACKAGE_URL?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
