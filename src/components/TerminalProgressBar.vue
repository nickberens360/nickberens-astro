<template>
  <div class="loading-container">
    <div
      class="progress-bar-container"
      :class="themeClass"
      role="progressbar"
      :aria-valuemin="0"
      :aria-valuemax="100"
      :aria-valuenow="progress"
    >
      <div
        class="progress-bar"
        :class="themeClass"
        :style="{ width: `${progress}%` }"
      ></div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TerminalProgressBar',
  props: {
    progress: {
      type: Number,
      default: 0,
      validator: (value) => value >= 0 && value <= 100
    },
    theme: {
      type: String,
      default: 'dark',
      validator: (value) => ['dark', 'light'].includes(value)
    }
  },
  computed: {
    themeClass() {
      return `theme-${this.theme}`;
    }
  }
};
</script>

<style scoped>
.loading-container {
  margin: 10px 0;
  width: 100%;
}

.progress-bar-container {
  width: 100%;
  height: 20px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 0;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #ffffff;
  border-radius: 0;
  transition: width 0.3s ease;
}

/* Theme variations */
.progress-bar-container.theme-light {
  background-color: rgba(0, 0, 0, 0.2);
}

.progress-bar.theme-light {
  background-color: #000000;
}

/* Dark theme styles are the default, no additional classes needed */
.progress-bar-container.theme-dark {
  background-color: rgba(255, 255, 255, 0.2);
}

.progress-bar.theme-dark {
  background-color: #ffffff;
}
</style>