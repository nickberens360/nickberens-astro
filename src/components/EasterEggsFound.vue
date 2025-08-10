<template>
  <Transition name="celebration">
    <div v-if="allEggsFound && showOverlay" class="celebration-overlay" @click="handleClose">
      <!-- Falling stars background -->
      <div class="stars-container">
        <div v-for="n in 50" :key="n" class="star" :style="getStarStyle(n)">
          ⭐
        </div>
      </div>

      <!-- Main content -->
      <div class="celebration-content">
        <div class="trophy-icon">🏆</div>
        <h1 class="celebration-title">
          <span class="rainbow-text">You did it!</span>
        </h1>
        <h2 class="celebration-subtitle">
          <span class="rainbow-text">All Easter eggs found!</span>
        </h2>

        <!-- Easter eggs summary -->
        <div class="eggs-summary">
          <div v-for="egg in easterEggs" :key="egg.name" class="egg-item">
            <span class="egg-icon">🥚</span>
            <span class="egg-hint">{{ egg.hint }}</span>
            <span class="egg-check">✅</span>
          </div>
        </div>

        <h3 class="gimme-a-job">If you give me a job I'll be able to afford a
          prize for you.</h3>

        <button class="close-button" @click.stop="handleClose">
          Continue Exploring
        </button>
      </div>

      <!-- Additional visual effects -->
      <div class="sparkles">
        <span v-for="n in 30" :key="n" class="sparkle" :style="getSparkleStyle(n)">✨</span>
      </div>
    </div>
  </Transition>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useStore } from '@nanostores/vue';
import { allEggsFound, easterEggsStore } from '../stores/easter-eggs.js';

export default {
  name: 'EasterEggsFound',
  setup() {
    const showOverlay = ref(false);
    const allEggsFoundValue = useStore(allEggsFound);
    const easterEggsData = useStore(easterEggsStore);

    // Check localStorage to see if celebration has been shown
    const CELEBRATION_SHOWN_KEY = 'nickgoldsworthy_celebration_shown';

    const hasShownCelebration = () => {
      if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
        return false;
      }
      return localStorage.getItem(CELEBRATION_SHOWN_KEY) === 'true';
    };

    const markCelebrationAsShown = () => {
      if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
        localStorage.setItem(CELEBRATION_SHOWN_KEY, 'true');
      }
    };

    // Reset celebration shown state when eggs are reset
    // This should be called from easter-eggs.js resetEasterEggs function
    // export const resetCelebrationShown = () => {
    //   if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
    //     localStorage.removeItem(CELEBRATION_SHOWN_KEY);
    //   }
    // };

    // Check if we should show the overlay
    const checkAndShowOverlay = () => {
      if (allEggsFoundValue.value && !hasShownCelebration()) {
        showOverlay.value = true;
        markCelebrationAsShown();
        // Prevent scrolling while overlay is shown
        document.body.style.overflow = 'hidden';
      }
    };

    // Watch for changes to allEggsFound
    watch(allEggsFoundValue, (newValue) => {
      if (newValue && !hasShownCelebration()) {
        checkAndShowOverlay();
      }
    });

    onMounted(() => {
      checkAndShowOverlay();
    });

    onUnmounted(() => {
      // Restore scrolling
      document.body.style.overflow = '';
    });

    const handleClose = () => {
      showOverlay.value = false;
      document.body.style.overflow = '';
    };

    // Generate random styles for falling stars
    const getStarStyle = (index) => {
      const left = Math.random() * 100;
      const animationDelay = Math.random() * 5;
      const animationDuration = 5 + Math.random() * 5;
      const size = 0.5 + Math.random() * 1.5;

      return {
        left: `${left}%`,
        fontSize: `${size}rem`,
        animationDelay: `${animationDelay}s`,
        animationDuration: `${animationDuration}s`
      };
    };

    // Generate random styles for sparkles
    const getSparkleStyle = (index) => {
      const top = Math.random() * 100;
      const left = Math.random() * 100;
      const animationDelay = Math.random() * 2;
      const size = 0.5 + Math.random() * 1;

      return {
        top: `${top}%`,
        left: `${left}%`,
        fontSize: `${size}rem`,
        animationDelay: `${animationDelay}s`
      };
    };

    return {
      allEggsFound: allEggsFoundValue,
      showOverlay,
      easterEggs: easterEggsData.value.easterEggs,
      handleClose,
      getStarStyle,
      getSparkleStyle
    };
  }
};
</script>

<style scoped>
/* Overlay container */
.celebration-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}

.gimme-a-job {
  font-size: 1.2rem;
  margin-top: 1rem;
  color: #ffeb3b;
  text-shadow: 0 0 5px rgba(255, 235, 59, 0.7);
}

/* Transition animations */
.celebration-enter-active,
.celebration-leave-active {
  transition: all 0.5s ease;
}

.celebration-enter-from {
  opacity: 0;
  transform: scale(1.1);
}

.celebration-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

/* Stars container and animation */
.stars-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.star {
  position: absolute;
  top: -50px;
  animation: falling linear infinite;
  filter: drop-shadow(0 0 10px rgba(255, 223, 0, 0.5));
}

@keyframes falling {
  from {
    transform: translateY(0) rotate(0deg);
  }
  to {
    transform: translateY(calc(100vh + 50px)) rotate(360deg);
  }
}

/* Main content */
.celebration-content {
  position: relative;
  z-index: 10;
  text-align: center;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 20px;
  backdrop-filter: blur(10px);
  box-shadow: 0 0 50px rgba(255, 255, 255, 0.2);
  max-width: 600px;
  animation: contentPulse 2s ease-in-out infinite;
}

@keyframes contentPulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.02);
  }
}

.trophy-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
  animation: bounce 1s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

/* Rainbow text effect */
.celebration-title {
  font-size: 3rem;
  margin: 0.5rem 0;
  font-weight: bold;
}

.celebration-subtitle {
  font-size: 2rem;
  margin: 0.5rem 0 2rem;
  font-weight: 600;
}

.rainbow-text {
  background: linear-gradient(
    90deg,
    #ff0000 0%,
    #ff7f00 14%,
    #ffff00 28%,
    #00ff00 42%,
    #0000ff 56%,
    #4b0082 70%,
    #9400d3 84%,
    #ff0000 100%
  );
  background-size: 200% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: rainbow 3s linear infinite;
}

@keyframes rainbow {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 200% 50%;
  }
}

/* Eggs summary */
.eggs-summary {
  margin: 2rem 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.egg-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: white;
  font-size: 1.1rem;
  animation: slideIn 0.5s ease-out backwards;
}

.egg-item:nth-child(1) {
  animation-delay: 0.1s;
}

.egg-item:nth-child(2) {
  animation-delay: 0.2s;
}

.egg-item:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.egg-icon {
  font-size: 1.5rem;
}

.egg-hint {
  flex: 1;
}

.egg-check {
  color: #4ade80;
  font-size: 1.3rem;
}

/* Close button */
.close-button {
  margin-top: 2rem;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.close-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.close-button:active {
  transform: translateY(0);
}

/* Sparkles */
.sparkles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.sparkle {
  position: absolute;
  animation: sparkle 2s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% {
    opacity: 0;
    transform: scale(0);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Responsive design */
@media (max-width: 768px) {
  .celebration-title {
    font-size: 2rem;
  }

  .celebration-subtitle {
    font-size: 1.5rem;
  }

  .trophy-icon {
    font-size: 4rem;
  }

  .celebration-content {
    margin: 1rem;
    padding: 1.5rem;
  }

  .egg-item {
    font-size: 1rem;
    padding: 0.5rem;
  }
}

@media (max-width: 480px) {
  .celebration-title {
    font-size: 1.75rem;
  }

  .celebration-subtitle {
    font-size: 1.25rem;
  }

  .egg-hint {
    font-size: 0.9rem;
  }
}
</style>