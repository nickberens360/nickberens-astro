<template>
  <div class="font-display" :class="{ 'fonts-loading': !fontCheckComplete || !fontsLoaded, 'fonts-ready': fontCheckComplete && fontsLoaded }">
    <div v-if="!fontCheckComplete || !fontsLoaded" class="loading-spinner">
      Loading font...
    </div>
    
    <h1 v-show="fontCheckComplete && fontsLoaded" class="font-display__title text-center">
      <span class="font-display__title-text">{{ fontName }}</span>
      <span v-if="needsFakeBold" class="font-display__title-fake-bold">{{ fontName }}</span>
    </h1>

    <div v-show="fontCheckComplete && fontsLoaded" class="font-display__controls">
      <input
        v-model="fontOutput"
        type="text"
        placeholder="Type something..."
        class="font-display__input"
      />
      <select v-model="fontSize" class="font-display__select">
        <option
          v-for="size in defaultSizes"
          :key="size"
          :value="`${size}px`"
        >
          {{ size }}px
        </option>
      </select>
    </div>

    <div v-show="fontCheckComplete && fontsLoaded" class="font-display__output" :style="{ fontSize }">
      <span class="font-display__output-text">{{ fontOutput }}</span>
      <span v-if="needsFakeBold" class="font-display__output-fake-bold">{{ fontOutput }}</span>
    </div>

    <div v-show="fontCheckComplete && fontsLoaded" class="font-container">
      <div class="font-container__content">
        <template v-for="(charset, index) in charsets" :key="index">
          {{ charset }}<br>
        </template>
      </div>

      <div v-if="needsFakeBold" class="font-container__fake-bold">
        <template v-for="(charset, index) in charsets" :key="`bold-${index}`">
          {{ charset }}<br>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const props = defineProps({
  fontData: {
    type: Object,
    default: () => ({
      name: 'Font Display',
      family: 'sans-serif',
      titleFontSize: '12vw'
    })
  }
});

const fontName = computed(() => props.fontData.name || 'Font Display');
const fontFamily = computed(() => props.fontData.family || 'sans-serif');
const fontOutput = ref('Try Me.');
const fontSize = ref('48px');
const titleFontSize = computed(() => props.fontData.titleFontSize || '12vw');

const fontsLoaded = ref(false);
const fontCheckComplete = ref(false);

const needsFakeBold = computed(() =>
  fontName.value === 'Dripity' || fontName.value === 'Kinda Sans Serif'
);

const defaultSizes = [12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72];

const charsets = [
  'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  'abcdefghijklmnopqrstuvwxyz',
  '1234567890',
  '&​.​,​?​!​@​(​)​#​$​%​+​-​=​:​;'
];

onMounted(async () => {
  // Add a small delay to ensure DOM is ready
  await new Promise(resolve => setTimeout(resolve, 10));
  
  try {
    const fontFace = `16px "${fontFamily.value}"`;
    
    // First, ensure font faces are defined
    if (document.fonts.size === 0) {
      // Wait for fonts to be registered
      await document.fonts.ready;
    }
    
    // Check if font is already loaded
    if (document.fonts.check(fontFace)) {
      fontsLoaded.value = true;
      fontCheckComplete.value = true;
      return;
    }

    // Force load the font
    const loadPromise = document.fonts.load(fontFace);
    const timeoutPromise = new Promise((resolve) => setTimeout(() => resolve('timeout'), 3000));
    
    // Race between font loading and timeout
    const result = await Promise.race([loadPromise, timeoutPromise]);
    
    if (result === 'timeout') {
      console.warn('Font loading timed out, showing content');
      fontsLoaded.value = true;
      fontCheckComplete.value = true;
      return;
    }
    
    // Wait for all fonts to be ready
    await document.fonts.ready;
    
    // Final check
    if (document.fonts.check(fontFace)) {
      fontsLoaded.value = true;
    } else {
      console.warn('Font not available, using fallback');
      fontsLoaded.value = true;
    }
    
    fontCheckComplete.value = true;
  } catch (error) {
    console.warn('Font loading error:', error);
    fontsLoaded.value = true;
    fontCheckComplete.value = true;
  }
});

</script>

<style scoped>
.font-display {
  position: relative;
  font-family: v-bind(fontFamily), sans-serif;
  padding: 16px;
  border-radius: 8px;
  opacity: 1;
  visibility: visible;
  transition: opacity 0.3s ease-in-out, visibility 0.3s ease-in-out;
}

.font-display.fonts-loading {
  opacity: 0;
  visibility: hidden;
}

.font-display.fonts-loading .loading-spinner {
  opacity: 1;
  visibility: visible;
}

.loading-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1.2rem;
  color: currentColor;
  z-index: 10;
}

.font-display__title {
  position: relative;
  font-size: v-bind(titleFontSize);
  font-weight: normal;
  margin-bottom: 24px;
}

.font-display__title-text {
  position: relative;
  z-index: 2;
}

.font-display__title-fake-bold {
  position: absolute;
  top: 0;
  left: 1px;
  z-index: 1;
  width: 100%;
}

.fake-bold {
  position: absolute;
  top: 0;
  left: 1px;
}

.font-display__controls {
  display: flex;
  gap: 16px;
}

.font-display__input,
.font-display__select {
  padding: 8px;
  font-size: 16px;
  box-shadow: none;
  outline: none;
  border: none;
  color: inherit;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.20);
}

.font-display__output {
  position: relative;
  font-size: 48px;
  margin: 48px 0;
  padding-bottom: 48px;
  border-bottom: 1px solid currentColor;
  min-height: 1.2em;
}

.font-display__output-text {
  position: relative;
  z-index: 2;
}

.font-display__output-fake-bold {
  position: absolute;
  top: 0;
  left: 1px;
  z-index: 1;
}

.font-container {
  position: relative;
  font-size: 9.5vw;
  word-wrap: break-word;
}

.font-container__content {
  position: relative;
  z-index: 2;
}

.font-container__fake-bold {
  position: absolute;
  top: 0;
  left: 1px;
  z-index: 1;
  width: 100%;
  pointer-events: none;
}

@media (max-width: 600px) {
  .font-display__controls {
    display: block;
  }

  .font-display__input,
  .font-display__select {
    margin-bottom: 16px;
    display: block;
    width: 100%;
  }
}
</style>
