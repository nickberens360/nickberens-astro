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
  mounted() {
    // Update the font items when component mounts
    if (this.fonts && this.fonts.length > 0) {
      console.log('FontMenuLoader: Loading fonts:', this.fonts);
      console.log('FontMenuLoader: Font count:', this.fonts.length);
      console.log('FontMenuLoader: First font:', this.fonts[0]);
      
      // Process fonts to ensure proper structure
      const processedFonts = this.fonts.map((font, index) => {
        console.log(`FontMenuLoader: Processing font ${index}:`, font);
        return {
          id: font.id || font.slug || `font-${index}`,
          data: font.data || font
        };
      });
      
      console.log('FontMenuLoader: Processed fonts:', processedFonts);
      updateFontItems(processedFonts);
    } else {
      console.warn('FontMenuLoader: No fonts provided or empty array');
      console.log('FontMenuLoader: Fonts prop value:', this.fonts);
    }
  },
  watch: {
    fonts: {
      handler(newFonts) {
        if (newFonts && newFonts.length > 0) {
          console.log('FontMenuLoader: Fonts changed:', newFonts);
          updateFontItems(newFonts);
        }
      },
      deep: true,
      immediate: true
    }
  }
};
</script>