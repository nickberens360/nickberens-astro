<template>
  <div>
    <div class="font-display">
      <h1 class="font-display__title">{{ fontData.name || 'Font Display' }}</h1>
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
          <option v-for="size in availableSizes" :key="size" :value="`${size}px`">
            {{ size }}px
          </option>
        </select>
      </div>
      <p
        class="font-display__output"
        :style="{ fontSize: fontSize }"
      >
        {{ fontOutput }}
      </p>
      <hr />
      <h2 class="font-display__example">
        {{ fontData.specimen || 'The quick brown fox jumps over the lazy dog.' }}
      </h2>
      <h3 class="font-display__example">
        THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG.
      </h3>
      <h4 class="font-display__example">
        {{ fontData.specimen || 'The quick brown fox jumps over the lazy dog.' }}
      </h4>
      <h5 class="font-display__example">
        THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG.
      </h5>
      <h6 class="font-display__example">
        {{ fontData.specimen || 'The quick brown fox jumps over the lazy dog.' }}
      </h6>
      <p class="font-display__paragraph">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do
        eiusmod. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
        do eiusmod. Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Sed do eiusmod.
      </p>
      <p class="font-display__paragraph">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do
        eiusmod. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
        do eiusmod. Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Sed do eiusmod.
      </p>

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
      category: 'display',
      weight: 400,
      description: '',
      specimen: 'The quick brown fox jumps over the lazy dog.',
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
const fontOutput = ref(props.fontData.specimen || 'Example.');
const fontSize = ref('24px');
const availableSizes = computed(() => props.fontData.sizes || [12, 14, 16, 18, 20, 24, 28, 32, 36]);
const titleFontWeight = computed(() => props.isTitleFontBold ? 'bold' : 'normal');
const titleFontSizeValue = computed(() => props.fontData.titleFontSize || props.titleFontSize);
</script>

<style scoped>
.font-display {
  font-family: v-bind(fontFamily), sans-serif;
  padding: 16px;
  border-radius: 8px;
}

.font-display__title {
  font-size: v-bind(titleFontSizeValue);
  font-weight: v-bind(titleFontWeight);
  margin-bottom: 24px;
}

.font-display__controls {
  display: flex;
  gap: 16px;
}

input, select {
  padding: 8px;
  font-size: 16px;
  box-shadow: none;
  outline: none;
  border: 1px solid currentColor;
  color: inherit;
  border-radius: 4px;
  background-color: transparent;
}

hr {
  margin: 32px 0;
  border: none;
  border-top: 1px solid black;
}

.font-display__output {
  font-family: v-bind(fontFamily), sans-serif;
  font-size: 24px;
  margin-bottom: 16px;
}
.font-display__example {
  font-family: v-bind(fontFamily), sans-serif;
  margin: 16px 0;
}
h2.font-display__example {
  font-size: 48px;
}
h3.font-display__example {
  font-size: 36px;
}
h4.font-display__example {
  font-size: 24px;
}
h5.font-display__example {
  font-size: 18px;
}
h6.font-display__example {
  font-size: 16px;
}
.font-display__paragraph {
  font-family: v-bind(fontFamily), sans-serif;
  font-size: 16px;
  line-height: 1.5;
  margin: 8px 0;
}
</style>