<template>
  <section class="hero-banner">
    <div class="hero-content">
      <div class="hero-banner__heading">
        <slot name="heading">
          <h1>
            One time I said the word
            <span class="highlight">{{ inputValue}}</span>
            during an interview&nbsp;🙀.
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
    console.log('HeroBanner mounted, terminalInputValue:', terminalInputValueStore);
    return {
      inputValue: terminalInputValueStore
    }
  }
}
</script>

<style>
.hero-banner {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: v-bind(backgroundColor);
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
