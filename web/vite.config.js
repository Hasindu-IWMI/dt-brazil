import { defineConfig } from 'vite';

// base './' makes the static build (web/dist) work from any folder or URL path,
// e.g. GitHub Pages at /<repo>/ or a plain file server.
export default defineConfig({ base: './', build: { target: 'es2022' } });
