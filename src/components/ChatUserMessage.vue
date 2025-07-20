<template>
  <p>{{ message.text }}</p>
</template>

<script>
export default {
  props: {
    message: {
      type: Object,
      required: true
    }
  }
};
</script>