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
  },
  setup(props) {
    const eyelashElement = ref(null);
    const isDragging = ref(false);
    const currentX = ref(props.initialX);
    const currentY = ref(props.initialY);
    const initialMouseX = ref(0);
    const initialMouseY = ref(0);

    const eyelashStyle = computed(() => ({
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

      // Safe pointer capture with error handling
      try {
        if (eyelashElement.value && event.pointerId !== undefined) {
          eyelashElement.value.setPointerCapture(event.pointerId);
        }
      } catch (e) {
        // Ignore errors if pointer capture is not supported or fails
        console.debug('Pointer capture failed:', e);
      }

      // Add listeners to window for better performance and standard drag pattern
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', stopDrag);
      window.addEventListener('pointercancel', stopDrag);

      // Prevent text selection and default behaviors
      event.preventDefault();
    };

    const handlePointerMove = (event) => {
      if (!isDragging.value || !event.isPrimary) return;

      currentX.value = event.clientX - initialMouseX.value;
      currentY.value = event.clientY - initialMouseY.value;

      // Keep the eyelash within viewport bounds using actual component dimensions
      const rect = eyelashElement.value?.getBoundingClientRect();
      const maxX = window.innerWidth - (rect?.width ?? 0);
      const maxY = window.innerHeight - (rect?.height ?? 0);

      currentX.value = Math.max(0, Math.min(currentX.value, maxX));
      currentY.value = Math.max(0, Math.min(currentY.value, maxY));
    };

    // Defensive cleanup function to ensure clean state
    const cleanup = () => {
      isDragging.value = false;
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDrag);
      window.removeEventListener('pointercancel', stopDrag);
    };

    const stopDrag = (event) => {
      // Remove primary pointer check to ensure cleanup always happens
      cleanup();

      // Safe pointer capture release with error handling
      try {
        if (eyelashElement.value && event.pointerId !== undefined) {
          eyelashElement.value.releasePointerCapture(event.pointerId);
        }
      } catch (e) {
        // Ignore errors if pointer capture was already released or not supported
        console.debug('Pointer capture release failed:', e);
      }
    };

    onUnmounted(() => {
      // Use defensive cleanup to ensure all listeners are removed
      cleanup();
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
  z-index: 9999;
  transition: none;
  opacity: .45;
  width: 44px;
  height: 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -khtml-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.eyelash-image {
  width: 20px;
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