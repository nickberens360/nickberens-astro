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
  vite: {
    // Ensure environment variables are properly loaded
    envPrefix: 'PUBLIC_',
    // Make non-prefixed env vars available to server-side code
    ssr: {
      noExternal: ['@fortawesome/fontawesome-svg-core']
    }
  }
});
