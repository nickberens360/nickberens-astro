<template>
  <div class="font-nav">
    <a v-if="prevFont" :href="`/fonts/${prevFont.id}`" class="nav-link prev">
      ← {{ prevFont.data.name }}
    </a>
    <div class="ml-auto mr-auto" />
    <a v-if="nextFont" :href="`/fonts/${nextFont.id}`" class="nav-link next">
      {{ nextFont.data.name }} →
    </a>
  </div>
</template>

<script>
export default {
  name: 'FontNavigation',
  props: {
    prevFont: {
      type: Object,
      default: null
    },
    nextFont: {
      type: Object,
      default: null
    }
  }
}
</script>

<style scoped>
.font-nav {
  position: relative;
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  z-index: 10;
}

.nav-link {
  color: inherit;
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
}

.nav-link:hover {
  background-color: transparent;
}
</style>