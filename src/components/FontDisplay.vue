<template>
  <div>
    <div class="font-display">
      <h1 class="font-display__title">
        <span
          class="fake-bold"
          v-if="fontData.name === 'Dripity' || fontData.name ===
              'Kinda Sans Serif'"
        >{{
            fontData.name ||
            'FontDisplay'
          }}</span>
        {{ fontData.name || 'Font Display' }}
      </h1>
      <div class="font-display__controls">
        <input
          v-model="fontOutput"
          type="text"
          placeholder="Type something..."
          class="font-display__input"
        />
        <select
          v-model="fontSize"
          class="font-display__select"
        >
          <option
            v-for="size in availableSizes"
            :key="size"
            :value="`${size}px`"
          >
            {{ size }}px
          </option>
        </select>
      </div>
      <p
        class="font-display__output"
        :style="{ fontSize: fontSize }"
        contenteditable="true"
        @input="handleContentEdit"
      >
        <span
          v-if="fontData.name === 'Dripity' || fontData.name ===
          'Kinda Sans Serif'"
          class="fake-bold"
        >
          {{ fontOutput }}
        </span>
        {{ fontOutput }}
      </p>
      <div class="font-container">
        ABCDEFGHIJKLMNOPQRSTUVWXYZ
        <br>
        abcdefghijklmnopqrstuvwxyz
        <br>
        1234567890
        <br>&amp;​.​,​?​!​@​(​)​#​$​%​+​-​=​:​;
        <span
          v-if="fontData.name === 'Dripity' || fontData.name ===
          'Kinda Sans Serif'"
        >
          <span class="fake-bold">
            ABCDEFGHIJKLMNOPQRSTUVWXYZ
          </span>
        <br>
        abcdefghijklmnopqrstuvwxyz
        <br>
        1234567890
        <br>&amp;​.​,​?​!​@​(​)​#​$​%​+​-​=​:​;
        </span>
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
      name: 'Drip',
      family: 'Drip',
      sizes: [12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72]
    })
  },
  isTitleFontBold: {
    type: Boolean,
    default: true
  },
  titleFontSize: {
    type: String,
    default: '12vw'
  }
});

const fontFamily = computed(() => props.fontData.family || 'Drip');
const fontOutput = ref('Try Me.');
const fontSize = ref('48px');
const availableSizes = computed(() => props.fontData.sizes || [12, 14, 16, 18, 20, 24, 28, 32, 36]);
const titleFontWeight = computed(() => props.isTitleFontBold ? 'bold' : 'normal');
const titleFontSizeValue = computed(() => props.fontData.titleFontSize || props.titleFontSize);

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
  font-size: v-bind(titleFontSizeValue);
  /*font-weight: v-bind(titleFontWeight);*/
  font-weight: normal;
  margin-bottom: 24px;
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

@media (max-width: 600px) {
  .font-display__controls {
    display: block;
  }

  input, select {
    margin-bottom: 16px;
    display: block;
  }

  input, select {
    width: 100%;
  }
}

input, select {
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
</style>
