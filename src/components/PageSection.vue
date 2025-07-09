<template>
  <section
    class="page-section"
    :class="{ 'page-section--full-height': fullHeight }"
    :style="{ backgroundColor: backgroundColor }"
  >
    <div
      class="page-section__inner"
      :style="{ maxWidth: width + 'px' }"
    >
      <slot></slot>
    </div>
  </section>
</template>

<script>
export default {
  name: 'PageSection',
  props: {
    backgroundColor: {
      type: String,
      default: 'transparent'
    },
    fullHeight: {
      type: Boolean,
      default: false
    },
    width: {
      type: [String, Number],
      default: 1400
    }
  }
}
</script>

<style scoped>
.page-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem 1.5rem;
}

.page-section--full-height {
  min-height: calc(100vh - var(--site-header-height));
  padding: 0 1.5rem;
}

.page-section__inner {
  width: 100%;
  margin: 0 auto;
}
</style>