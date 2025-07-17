<template>
  <div v-if="isMounted">
    <slot></slot>
  </div>
  <div v-else style="display: none;"></div>
</template>

<script>
export default {
  name: 'ClientOnly',
  data() {
    return {
      isMounted: false
    }
  },
  mounted() {
    this.isMounted = true
  }
}
</script>