<template>
  <div
    ref="eyelashElement"
    class="annoying-eyelash"
    :style="eyelashStyle"
    @pointerdown="startDrag"
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
      zIndex: 50,
      width: `${props.size}px`,
      top: `${currentY.value}px`,
      left: `${currentX.value}px`,
      cursor: 'move',
      userSelect: 'none',
      touchAction: 'none' // Prevent default touch behaviors
    }));

    const startDrag = (event) => {
      // Only handle primary pointer (first finger/mouse)
      if (!event.isPrimary) return;

      isDragging.value = true;
      initialMouseX.value = event.clientX - currentX.value;
      initialMouseY.value = event.clientY - currentY.value;

      // Capture pointer for this element
      eyelashElement.value.setPointerCapture(event.pointerId);

      // Prevent text selection and default behaviors
      event.preventDefault();
    };

    const handlePointerMove = (event) => {
      if (!isDragging.value || !event.isPrimary) return;

      currentX.value = event.clientX - initialMouseX.value;
      currentY.value = event.clientY - initialMouseY.value;

      // Keep the eyelash within viewport bounds
      const maxX = window.innerWidth - props.size;
      const maxY = window.innerHeight - props.size;

      currentX.value = Math.max(0, Math.min(currentX.value, maxX));
      currentY.value = Math.max(0, Math.min(currentY.value, maxY));
    };

    const stopDrag = (event) => {
      if (!event.isPrimary) return;

      isDragging.value = false;

      // Release pointer capture
      if (eyelashElement.value) {
        eyelashElement.value.releasePointerCapture(event.pointerId);
      }
    };

    onMounted(() => {
      const element = eyelashElement.value;
      element.addEventListener('pointermove', handlePointerMove);
      element.addEventListener('pointerup', stopDrag);
      element.addEventListener('pointercancel', stopDrag);
    });

    onUnmounted(() => {
      const element = eyelashElement.value;
      if (element) {
        element.removeEventListener('pointermove', handlePointerMove);
        element.removeEventListener('pointerup', stopDrag);
        element.removeEventListener('pointercancel', stopDrag);
      }
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
  position: fixed;
  transition: none;
  /* Prevent text selection on all devices */
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -khtml-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
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