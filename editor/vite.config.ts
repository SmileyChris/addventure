import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { gamesPlugin } from './vite-plugin-games';

export default defineConfig({
  plugins: [svelte(), gamesPlugin()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    globals: true,
    passWithNoTests: true,
  },
});
