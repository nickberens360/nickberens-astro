<template>
  <div class="skeleton-loader">
    <!-- Header skeleton -->
    <div class="skeleton-header"></div>

    <!-- Paragraph skeleton (two lines) -->
    <div class="skeleton-paragraph">
      <div class="skeleton-line"></div>
      <div class="skeleton-line skeleton-line-short"></div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SkeletonLoader'
}
</script>

<style scoped>
.skeleton-loader {
  padding: 16px;
  max-width: 100%;
}

.skeleton-header {
  height: 32px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 16px;
}

.skeleton-paragraph {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
}

.skeleton-line-short {
  width: 75%;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Dark mode support */
/*@media (prefers-color-scheme: dark) {
  .skeleton-header,
  .skeleton-line {
    background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
    background-size: 200% 100%;
  }
}*/
</style>
