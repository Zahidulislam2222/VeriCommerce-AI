import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { copyFileSync } from 'node:fs';
import { resolve } from 'node:path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'DEV_');
  const target = env.DEV_API_TARGET;
  if (target) {
    const url = new URL(target);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('DEV_API_TARGET must be an HTTP(S) URL without credentials.');
  }
  return { plugins: [react(), { name: 'public-not-found', closeBundle() {
    copyFileSync(resolve('dist/index.html'), resolve('dist/404.html'));
  } }], build: { sourcemap: false },
    server: { proxy: target ? { '/api': { target, changeOrigin: false } } : undefined } };
});
