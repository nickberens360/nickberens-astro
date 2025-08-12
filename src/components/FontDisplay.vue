<template>
  <div class="font-display">
    <h1 class="font-display__title text-center">
      <span class="font-display__title-text">{{ fontName }}</span>
      <span v-if="needsFakeBold" class="font-display__title-fake-bold">{{ fontName }}</span>
    </h1>

    <div class="font-display__controls">
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

    <p
      class="font-display__output"
      :style="{ fontSize }"
      contenteditable="true"
      @input="handleContentEdit"
    >
      <span v-if="needsFakeBold" class="fake-bold">{{ fontOutput }}</span>
      {{ fontOutput }}
    </p>

    <div class="font-container">
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
import { ref, computed } from 'vue';

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

const handleContentEdit = (event) => {
  fontOutput.value = event.target.textContent;
};
</script>

<style scoped>
.font-display {
  position: relative;
  font-family: v-bind(fontFamily), sans-serif;
  padding: 16px;
  border-radius: 8px;
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
  margin-bottom: 48px;
  border-bottom: 1px solid currentColor;
}

.font-container {
  position: relative;
  font-size: 10.5vw;
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
