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
          const processedFonts = newFonts.map((font, index) => ({
            id: font.id || font.slug || `font-${index}`,
            data: font.data || font
          }));
          updateFontItems(processedFonts);
        }
      },
      deep: true,
      immediate: true
    }
  }
};
</script>