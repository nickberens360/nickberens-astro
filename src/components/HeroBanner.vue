<template>
  <section class="hero-banner">
    <div class="hero-content">
      <div class="hero-banner__heading">
        <slot name="heading">
          <h1>
            One time I said a
            <span class="highlight">bad&nbsp;word</span>
            during an interview&nbsp;🤦‍♂️.
          </h1>
        </slot>
      </div>
      <slot name="content">
        <p v-if="content">{{ content }}</p>
      </slot>
    </div>
  </section>
</template>

<script>
import { useStore } from '@nanostores/vue';
import { terminalInputValue } from '../stores/ui';

export default {
  name: 'HeroBanner',
  props: {
    heading: {
      type: String,
      default: ''
    },
    content: {
      type: String,
      default: ''
    },
    backgroundColor: {
      type: String,
      default: '#d3a6fe'
    }
  },
  setup() {
    const terminalInputValueStore = useStore(terminalInputValue);
    return {
      inputValue: terminalInputValueStore
    }
  }
}
</script>

<style>
.hero-banner {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: v-bind(backgroundColor);
}

@supports not (height: 100dvh) {
  .hero-banner {
    min-height: 100vh;
  }
}

@supports (height: 100dvh) {
  .hero-banner {
    height: 100dvh;
  }
}

.hero-content {
  text-align: center;
  padding: 1rem;
}

.hero-banner__heading  *{
  margin-bottom: 1rem;
  font-size: clamp(2.5rem, 7vw, 10.5rem);

}
</style>
