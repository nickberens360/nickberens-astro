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
  --card-title-size: clamp(1.3rem, 1.3rem + 0.5vw, 1.8rem);
  --card-text-size: clamp(0.9rem, 0.9rem + 0.2vw, 1.1rem);
  --card-meta-size: clamp(0.8rem, 0.8rem + 0.1vw, 0.9rem);
  --card-spacing-sm: clamp(0.4rem, 0.5vw, 0.7rem);
  --card-spacing-md: clamp(0.8rem, 1vw, 1.2rem);

  border-radius: 8px;
  padding: 1.5rem;
  background-color: rgb(255 255 255 / 26%);
  transition: transform 0.2s ease;
}

.blog-post-card:hover {
  transform: translateY(-5px);
}

.blog-post-card__title {
  margin-top: 0;
  margin-bottom: clamp(0.4rem, 0.5vw, 0.7rem);
  font-size: clamp(1.3rem, 1.3rem + 0.5vw, 1.8rem);
}

.blog-post-card__title a {
  color: inherit;
  text-decoration: none;
}

.blog-post-card__title a:hover {
  text-decoration: underline;
}

.blog-post-card__description {
  margin-bottom: clamp(0.8rem, 1vw, 1.2rem);
  font-size: clamp(0.9rem, 0.9rem + 0.2vw, 1.1rem);
  line-height: clamp(1.4, 1.4 + 0.1vw, 1.6);
}

.blog-post-card__meta {
  margin-top: clamp(0.8rem, 1vw, 1.2rem);
  font-size: clamp(0.8rem, 0.8rem + 0.1vw, 0.9rem);
  color: #666;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
