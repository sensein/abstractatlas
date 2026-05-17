/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_BUILD_SHA?: string;
	readonly VITE_BUILD_SHA_SHORT?: string;
	readonly VITE_BUILD_AT?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
