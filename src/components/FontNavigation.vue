<template>
  <div class="font-nav">
    <div class="mr-auto" />
    <a v-if="prevFont" :href="`/fonts/${prevFont.id}`" class="nav-link prev">
      ← {{ prevFont.data.name }}
    </a>
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
  top: 1rem;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0 2rem;
  z-index: 10;
}

.nav-link {
  color: inherit;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.nav-link.home {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
</style>