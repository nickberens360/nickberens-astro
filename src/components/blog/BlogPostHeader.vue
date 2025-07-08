<template>
  <div class="blog-post-header">
    <h1 class="blog-post-header__title">{{ title }}</h1>
    <div class="blog-post-header__meta">
      <time :datetime="pubDate.toISOString()">
        {{ formatDate(pubDate) }}
      </time>
      <span v-if="author" class="blog-post-header__author">by {{ author }}</span>
    </div>
    <BlogTags v-if="tags && tags.length > 0" :tags="tags" />
  </div>
</template>

<script>
import BlogTags from './BlogTags.vue';

export default {
  name: 'BlogPostHeader',
  components: {
    BlogTags
  },
  props: {
    title: {
      type: String,
      required: true
    },
    pubDate: {
      type: Date,
      required: true
    },
    author: {
      type: String,
      default: ''
    },
    tags: {
      type: Array,
      default: () => []
    }
  },
  methods: {
    formatDate(date) {
      return date.toLocaleDateString('en-us', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    }
  }
}
</script>

<style scoped>
.blog-post-header {
  margin-bottom: 2rem;
}

.blog-post-header__title {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.blog-post-header__meta {
  color: #666;
  margin-bottom: 1rem;
  display: flex;
  gap: 1rem;
}

.blog-post-header__author {
  font-style: italic;
}
</style>