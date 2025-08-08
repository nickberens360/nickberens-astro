<template>
  <div
    v-if="isComponentVisible"
    ref="eyelashElement"
    class="annoying-eyelash"
    :class="{ 'animating': isAnimating }"
    :style="eyelashStyle"
    @pointerdown="startDrag"
  >
    <img
      v-if="!isEmoji"
      src="/images/eyelash.png"
      alt="Eyelash"
      class="eyelash-image"
      draggable="false"
    />
    <div
      v-else
      class="emoji-display"
      :class="{ 'animate-up-flip': isAnimating }"
      @animationend="onAnimationEnd"
      @webkitAnimationEnd="onAnimationEnd"
    >
      🤭
    </div>
  </div>
</template>

<script>
import { ref, computed, onUnmounted } from 'vue';

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
    const dragAttempts = ref(0);
    const isAnimating = ref(false);
    const isComponentVisible = ref(true);

    const eyelashStyle = computed(() => ({
      top: `${currentY.value}px`,
      left: `${currentX.value}px`,
      cursor: 'move',
      userSelect: 'none',
      touchAction: 'none' // Prevent default touch behaviors
    }));

    const isEmoji = computed(() => dragAttempts.value >= 3);

    const startDrag = (event) => {
      if (!event.isPrimary) return;

      dragAttempts.value++;

      isDragging.value = true;
      initialMouseX.value = event.clientX - currentX.value;
      initialMouseY.value = event.clientY - currentY.value;

      try {
        if (eyelashElement.value && event.pointerId !== undefined) {
          eyelashElement.value.setPointerCapture(event.pointerId);
        }
      } catch (e) {
        console.debug('Pointer capture failed:', e);
      }

      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', stopDrag);
      window.addEventListener('pointercancel', stopDrag);

      event.preventDefault();
    };

    const handlePointerMove = (event) => {
      if (!isDragging.value || !event.isPrimary) return;

      currentX.value = event.clientX - initialMouseX.value;
      currentY.value = event.clientY - initialMouseY.value;

      const rect = eyelashElement.value?.getBoundingClientRect();
      const maxX = window.innerWidth - (rect?.width ?? 0);
      const maxY = window.innerHeight - (rect?.height ?? 0);

      currentX.value = Math.max(0, Math.min(currentX.value, maxX));
      currentY.value = Math.max(0, Math.min(currentY.value, maxY));
    };

    const cleanup = () => {
      isDragging.value = false;
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDrag);
      window.removeEventListener('pointercancel', stopDrag);
    };

    const stopDrag = (event) => {
      if (!event.isPrimary) return;

      cleanup();

      // Trigger on the 3rd attempt
      if (dragAttempts.value === 3) {
        // Tiny delay to avoid event queue conflicts
        setTimeout(() => {
          isAnimating.value = true;
        }, 100);
      }

      try {
        if (eyelashElement.value && event.pointerId !== undefined) {
          eyelashElement.value.releasePointerCapture(event.pointerId);
        }
      } catch (e) {
        console.debug('Pointer capture release failed:', e);
      }
    };

    const onAnimationEnd = () => {
      isComponentVisible.value = false;
    };

    onUnmounted(() => {
      cleanup();
    });

    return {
      eyelashElement,
      eyelashStyle,
      startDrag,
      isEmoji,
      isAnimating,
      isComponentVisible,
      onAnimationEnd
    };
  }
};
</script>

<style scoped>
.annoying-eyelash {
  position: fixed;
  z-index: 9999;
  transition: none;
  width: 44px;
  height: 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  /* interaction + selection */
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -khtml-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;

  /* ✅ put perspective on the parent (iOS likes this) */
  perspective: 800px;
  -webkit-perspective: 800px;
}

.eyelash-image {
  width: 30px;
  height: auto;
  pointer-events: none;
  display: block;
  opacity: 0.45;
}

/* Prevent image dragging */
.eyelash-image {
  -webkit-user-drag: none;
  -khtml-user-drag: none;
  -moz-user-drag: none;
  -o-user-drag: none;
  user-drag: none;
}

.emoji-display {
  font-size: 48px;
  pointer-events: none;
  display: inline-block; /* ensure transforms behave consistently */
  line-height: 1;
  transform-origin: center center;
  -webkit-transform-origin: center center;
}

/* ---------- Keyframes (prefixed + unprefixed) ---------- */
@-webkit-keyframes upAndFlip {
  0% {
    -webkit-transform: translate3d(0, 0, 0) rotateY(0deg);
    transform: translate3d(0, 0, 0) rotateY(0deg);
    opacity: 1;
  }
  100% {
    -webkit-transform: translate3d(0, -100px, 0) rotateY(359deg);
    transform: translate3d(0, -100px, 0) rotateY(359deg);
    opacity: 1;
  }
}
@keyframes upAndFlip {
  0% {
    -webkit-transform: translate3d(0, 0, 0) rotateY(0deg);
    transform: translate3d(0, 0, 0) rotateY(0deg);
    opacity: 1;
  }
  100% {
    -webkit-transform: translate3d(0, -100px, 0) rotateY(359deg);
    transform: translate3d(0, -100px, 0) rotateY(359deg);
    opacity: 1;
  }
}

.animate-up-flip {
  /* kick off animation with prefixes */
  -webkit-animation: upAndFlip 1s ease-out forwards;
  animation: upAndFlip 1s ease-out forwards;

  /* render hints */
  will-change: transform;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
  -webkit-transform-style: preserve-3d;
  transform-style: preserve-3d;

  /* ensure the element is on its own layer from the start */
  -webkit-transform: translate3d(0, 0, 0);
  transform: translate3d(0, 0, 0);
}

/* Optional: tiny type smoothing on iOS */
@supports (-webkit-touch-callout: none) {
  .animate-up-flip {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
}
</style>
