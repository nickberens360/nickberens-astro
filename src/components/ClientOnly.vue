<template>
  <template v-if="isMounted">
    <slot></slot>
  </template>
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