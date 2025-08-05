<template>
  <div
    ref="eyelashElement"
    class="annoying-eyelash"
    :style="eyelashStyle"
    @mousedown="startDrag"
  >
    <img
      src="/images/eyelash.png"
      alt="Eyelash"
      class="eyelash-image"
      draggable="false"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';

export default {
  name: 'AnnoyingEyelash',
  props: {
    initialX: {
      type: Number,
      default: 50
    },
    initialY: {
      type: Number,
      default: 150
    },
    opacity: {
      type: Number,
      default: 0.5
    },
    size: {
      type: Number,
      default: 20
    }
  },
  setup(props) {
    const eyelashElement = ref(null);
    const isDragging = ref(false);
    const currentX = ref(props.initialX);
    const currentY = ref(props.initialY);
    const initialMouseX = ref(0);
    const initialMouseY = ref(0);

    const eyelashStyle = computed(() => ({
      opacity: props.opacity,
      position: 'fixed',
      zIndex: 50,
      width: `${props.size}px`,
      top: `${currentY.value}px`,
      left: `${currentX.value}px`,
      cursor: 'move',
      userSelect: 'none'
    }));

    const startDrag = (event) => {
      isDragging.value = true;
      initialMouseX.value = event.clientX - currentX.value;
      initialMouseY.value = event.clientY - currentY.value;

      // Prevent text selection during drag
      event.preventDefault();
    };

    const handleMouseMove = (event) => {
      if (!isDragging.value) return;

      currentX.value = event.clientX - initialMouseX.value;
      currentY.value = event.clientY - initialMouseY.value;

      // Keep the eyelash within viewport bounds
      const maxX = window.innerWidth - props.size;
      const maxY = window.innerHeight - props.size;

      currentX.value = Math.max(0, Math.min(currentX.value, maxX));
      currentY.value = Math.max(0, Math.min(currentY.value, maxY));
    };

    const stopDrag = () => {
      isDragging.value = false;
    };

    onMounted(() => {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', stopDrag);
    });

    onUnmounted(() => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', stopDrag);
    });

    return {
      eyelashElement,
      eyelashStyle,
      startDrag
    };
  }
};
</script>

<style scoped>
.annoying-eyelash {
  transition: none;
}

.eyelash-image {
  width: 100%;
  height: auto;
  pointer-events: none;
  display: block;
}

/* Prevent image dragging */
.eyelash-image {
  -webkit-user-drag: none;
  -khtml-user-drag: none;
  -moz-user-drag: none;
  -o-user-drag: none;
  user-drag: none;
}
</style>