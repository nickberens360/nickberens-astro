<template>
  <a :href="`/fonts/${font.id}`" class="font-card">
    <h2 class="font-card__title" :style="`font-family: '${font.data.family}', sans-serif;`">
      {{ font.data.name }}
    </h2>
    <p class="font-card__category">{{ font.data.category }}</p>
    <p class="font-card__specimen" :style="`font-family: '${font.data.family}', sans-serif;`">
      {{ font.data.specimen }}
    </p>
  </a>
</template>

<script>
export default {
  name: 'FontCard',
  props: {
    font: {
      type: Object,
      required: true
    }
  }
}
</script>

<style scoped>
.font-card {
  display: block;
  padding: 2rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  transition: all 0.2s ease;
  background: white;
}

.font-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #ccc;
}

.font-card__title {
  font-size: 2.5rem;
  margin: 0 0 0.5rem 0;
  line-height: 1.2;
  color: #222;
}

.font-card__category {
  font-size: 0.875rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 1rem 0;
}

.font-card__specimen {
  font-size: 1.125rem;
  line-height: 1.5;
  margin: 0;
  color: #444;
}
</style>