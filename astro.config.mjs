import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import mdx from '@astrojs/mdx';
import icon from "astro-icon";

export default defineConfig({
  integrations: [
    vue({
      appEntrypoint: '/src/app'
    }),
    mdx(),
    icon({
      // Define the icon packs to include
      include: {
        'fa-brands': ['twitter', 'github', 'linkedin']
      }
    })
  ],
});
