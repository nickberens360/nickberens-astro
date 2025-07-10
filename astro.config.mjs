import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import mdx from '@astrojs/mdx';
import icon from "astro-icon";

export default defineConfig({
  integrations: [
    vue(),
    mdx(),
    icon({
      // Define the icon packs to include
      include: {
        'fa-brands': ['twitter', 'github', 'linkedin']
      }
    })
  ],
  build: {
    inlineStylesheets: 'auto', // 'auto' or 'always' to inline small stylesheets
  },
  vite: {
    build: {
      cssMinify: true,
      cssCodeSplit: true,
    },
    css: {
      // Enable CSS code splitting
      splitSelectors: true,
    }
  }
});
