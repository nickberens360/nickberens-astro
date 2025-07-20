<template>
  <div class="image-gallery fade-in">
    <img
      v-for="src in images"
      :key="src"
      :src="src"
      alt="Illustration"
      class="chat-image"
      @click="$emit('image-click', src)"
    />
  </div>
</template>

<script>
export default {
  props: {
    images: {
      type: Array,
      required: true
    }
  },
  emits: ['image-click']
};
</script>

<style scoped>
.fade-in {
  opacity: 0;
  animation: fadeInUp 0.5s ease-out 0.2s forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.image-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.chat-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #444444;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.chat-image:hover {
  transform: scale(1.05);
}
</style>