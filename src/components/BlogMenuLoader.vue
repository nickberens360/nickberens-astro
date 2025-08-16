<template>
  <!-- This component doesn't render anything, it just loads blog data -->
</template>

<script>
import { updateBlogItems } from '../stores/ui.js';

export default {
  name: 'BlogMenuLoader',
  props: {
    posts: {
      type: Array,
      required: true
    }
  },
  watch: {
    posts: {
      handler(newPosts) {
        if (newPosts && newPosts.length > 0) {
          // Sort posts by date (newest first) before adding to menu
          const sortedPosts = [...newPosts].sort((a, b) => {
            const dateA = a.data?.pubDate || a.pubDate || new Date(0);
            const dateB = b.data?.pubDate || b.pubDate || new Date(0);
            return dateB.valueOf() - dateA.valueOf();
          });
          
          // Limit to most recent 10 posts for the dropdown
          const recentPosts = sortedPosts.slice(0, 10);
          
          updateBlogItems(recentPosts);
        }
      },
      deep: true,
      immediate: true
    }
  }
};
</script>