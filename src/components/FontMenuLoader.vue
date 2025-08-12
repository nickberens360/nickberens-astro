<template>
  <!-- This component doesn't render anything, it just loads font data -->
</template>

<script>
import { updateFontItems } from '../stores/ui.js';

export default {
  name: 'FontMenuLoader',
  props: {
    fonts: {
      type: Array,
      required: true
    }
  },
  watch: {
    fonts: {
      handler(newFonts) {
        if (newFonts && newFonts.length > 0) {
          // Astro content collections return objects with id, slug, data properties
          const processedFonts = newFonts.map((font, index) => {
            // If font already has the expected structure from Astro
            if (font.data && font.id) {
              return font;
            }
            // Fallback for other structures
            return {
              id: font.id || font.slug || `font-${index}`,
              data: font.data || font
            };
          });
          updateFontItems(processedFonts);
        } else {
          console.log('No fonts to process');
        }
      },
      deep: true,
      immediate: true
    }
  }
};
</script>