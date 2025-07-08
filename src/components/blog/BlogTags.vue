<template>
  <div class="blog-tags">
    <span v-for="tag in tags" :key="tag" class="blog-tag">{{ tag }}</span>
  </div>
</template>

<script>
export default {
  name: 'BlogTags',
  props: {
    tags: {
      type: Array,
      required: true
    }
  }
}
</script>

<style scoped>
.blog-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.blog-tag {
  background-color: #f0f0f0;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}
</style>