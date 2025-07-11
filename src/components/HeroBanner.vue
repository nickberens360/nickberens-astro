<template>
  <section class="hero-banner">
    <div class="hero-content">
      <div class="hero-banner__heading">
      <slot name="heading">
        <h1>{{heading}}</h1>
      </slot>
      </div>
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
    },
    backgroundColor: {
      type: String,
      default: '#d3a6fe'
    }
  }
}
</script>

<style>
.hero-banner {
  min-height: 100vh;
  min-height: -webkit-fill-available;
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
