<template>
  <div class="blog-post-card">
    <h2 class="blog-post-card__title">
      <a :href="`/blog/${post.slug}`">{{ post.data.title }}</a>
    </h2>
    <p class="blog-post-card__description">{{ post.data.description }}</p>
    <div class="blog-post-card__meta">
      <time :datetime="post.data.pubDate.toISOString()">
        {{ formatDate(post.data.pubDate) }}
      </time>
      <BlogTags v-if="post.data.tags" :tags="post.data.tags" />
    </div>
  </div>
</template>

<script>
import BlogTags from './BlogTags.vue';

export default {
  name: 'BlogPostCard',
  components: {
    BlogTags
  },
  props: {
    post: {
      type: Object,
      required: true
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
.blog-post-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s ease;
}

.blog-post-card:hover {
  transform: translateY(-5px);
}

.blog-post-card__title {
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.blog-post-card__title a {
  color: inherit;
  text-decoration: none;
}

.blog-post-card__title a:hover {
  text-decoration: underline;
}

.blog-post-card__description {
  margin-bottom: 1rem;
}

.blog-post-card__meta {
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #666;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>