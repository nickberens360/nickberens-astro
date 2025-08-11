<template>
  <div
    v-if="isComponentVisible && !hideAnnoyingEyelash"
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
      width="30"
      height="24"
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
      <div class="emoji-container">
        <span class="emoji-trophy">🏆</span>
        <span class="emoji-egg">🥚</span>
        <span class="emoji-star">⭐</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onUnmounted, onMounted, watch } from 'vue';
import { updateEasterEgg, updateAnnoyingEyelash, easterEggsStore } from '../stores/easter-eggs.js';
import { useStore } from '@nanostores/vue';

const DRAG_ATTEMPTS_THRESHOLD = 2;

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
    hideAnnoyingEyelash: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const eyelashElement = ref(null);
    const isDragging = ref(false);
    const initialMouseX = ref(0);
    const initialMouseY = ref(0);
    
    // Get state from store
    const $easterEggsStore = useStore(easterEggsStore);
    const eyelashState = computed(() => $easterEggsStore.value.annoyingEyelash || {});
    
    // Always initialize with props to avoid hydration mismatch
    const currentX = ref(props.initialX);
    const currentY = ref(props.initialY);
    const dragAttempts = ref(0);
    const isAnimating = ref(false);
    const isComponentVisible = ref(true);
    
    // Track if we've loaded stored position
    const hasLoadedStoredPosition = ref(false);
    
    // Watch for store changes and update local refs
    watch(() => eyelashState.value, (newState) => {
      currentX.value = newState.currentX ?? currentX.value;
      currentY.value = newState.currentY ?? currentY.value;
      dragAttempts.value = newState.dragAttempts ?? dragAttempts.value;
      isAnimating.value = newState.isAnimating ?? isAnimating.value;
      isComponentVisible.value = newState.isComponentVisible ?? isComponentVisible.value;
    }, { deep: true });

    const eyelashStyle = computed(() => ({
      top: `${currentY.value}px`,
      left: `${currentX.value}px`,
      cursor: 'move',
      userSelect: 'none',
      touchAction: 'none' // Prevent default touch behaviors
    }));

    const isEmoji = computed(() => dragAttempts.value >= DRAG_ATTEMPTS_THRESHOLD);

    const startDrag = (event) => {
      if (!event.isPrimary) return;

      dragAttempts.value++;
      updateAnnoyingEyelash({ dragAttempts: dragAttempts.value });

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
      
      // Update store with new position
      updateAnnoyingEyelash({ 
        currentX: currentX.value, 
        currentY: currentY.value 
      });
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

      // Trigger on the 2nd attempt
      if (dragAttempts.value === 2) {
        setTimeout(() => {
          isAnimating.value = true;
          updateAnnoyingEyelash({ isAnimating: true });
        }, 100);
        setTimeout(() => {
          updateEasterEgg('egg1');
        }, 1200);

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
      updateAnnoyingEyelash({ isComponentVisible: false });
    };

    // Load stored position after mount to avoid hydration mismatch
    onMounted(() => {
      const defaultX = 50;
      const defaultY = 150;
      const storedX = eyelashState.value.currentX;
      const storedY = eyelashState.value.currentY;
      
      // Check if we have a stored position
      const hasStoredPosition = storedX !== undefined && storedY !== undefined;
      
      if (hasStoredPosition) {
        // Use stored position
        currentX.value = storedX;
        currentY.value = storedY;
        dragAttempts.value = eyelashState.value.dragAttempts ?? 0;
        isAnimating.value = eyelashState.value.isAnimating ?? false;
        isComponentVisible.value = eyelashState.value.isComponentVisible ?? true;
        hasLoadedStoredPosition.value = true;
      } else {
        // Save initial props position to store
        updateAnnoyingEyelash({ 
          currentX: currentX.value, 
          currentY: currentY.value,
          isComponentVisible: true
        });
      }
    });
    
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
  z-index: var(--z-index-highest);
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
  display: inline-block;
  line-height: 1;
  transform-origin: center center;
  -webkit-transform-origin: center center;
}

.emoji-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.emoji-trophy {
  position: absolute;
  right: -10px;
  top: 15px;
  font-size: 34px;
}

.emoji-star {
  position: absolute;
  left: -10px;
  top: 15px;
  font-size: 34px;
}

@keyframes upAndFlip {
  0% {
    transform: translateY(0) rotateY(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(-100px) rotateY(359.9deg);
    opacity: 1;
  }
}

.animate-up-flip {
  animation: upAndFlip 1s ease-out forwards;
}

</style>
