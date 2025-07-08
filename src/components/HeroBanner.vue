<template>
  <section class="hero-banner">
    <div class="hero-content">
      <slot name="heading">
        <h2 class="hero-banner__heading">This one time I said the word
          <span class="highlight">Sh!t</span>
          during&nbspan interview&nbsp🙀.</h2>
      </slot>
      <slot name="content">
        <p v-if="content">{{ content }}</p>
      </slot>
    </div>
  </section>
</template>

<script>
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
    }
  }
}
</script>

<style scoped>
.hero-banner {
  height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #d3a6fe;
}

.hero-content {
  text-align: center;
  padding: 1rem;
}

.hero-banner__heading {
  /*font-family: 'Doto Variable', sans-serif;
  font-weight: 900 !important;*/
  margin-bottom: 1rem;
  font-size: clamp(4rem, 8vw, 10.5rem);
}

.highlight {
  background-color: black;
  color: white;
  font-weight: bold;
  padding: 0.2rem 1rem;
}
</style>
