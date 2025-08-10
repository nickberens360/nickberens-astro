<template>
  <div
    v-if="!hideEggs"
    ref="containerRef"
    class="easter-egg-container"
    @click.stop="toggleMenu"
  >
    <div
      v-if="isMenuVisible"
      class="easter-egg__menu"
      @click.stop
    >
      <p>{{ easterEggs.activeEggsCompleteCount }}/{{ easterEggs.totalEggsToComplete }} Easter Eggs Found</p>
      <ol>
        <li v-for="egg in easterEggs.easterEggs" :key="egg.name">
          {{ egg.isComplete ? '✅' : '❌' }} {{ egg.hint }}
        </li>
      </ol>
    </div>
    <span class="easter-egg__count">{{ easterEggs.activeEggsCompleteCount }}</span>
    <span class="easter-egg__icon">{{ allFound ? '🥚' : '🪺' }}</span>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useStore } from '@nanostores/vue';
import { easterEggsStore, allEggsFound } from '../stores/easter-eggs.js';

export default {
  name: 'EasterEgg',
  props: {
    hideEggs: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const easterEggs = useStore(easterEggsStore);
    const allFound = useStore(allEggsFound);
    const isMenuVisible = ref(false);
    const containerRef = ref(null);

    const toggleMenu = () => {
      isMenuVisible.value = !isMenuVisible.value;
    };

    const handleClickOutside = (event) => {
      if (containerRef.value && !containerRef.value.contains(event.target)) {
        isMenuVisible.value = false;
      }
    };

    // Watch for changes in completed eggs count
    watch(() => easterEggs.value.activeEggsCompleteCount, (newCount, oldCount) => {
      // Open menu when count increases (new egg found)
      if (newCount > oldCount) {
        isMenuVisible.value = true;
      }
    });

    onMounted(() => {
      document.addEventListener('click', handleClickOutside);
    });

    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside);
    });

    return {
      easterEggs,
      allFound,
      isMenuVisible,
      toggleMenu,
      containerRef
    };
  }
};
</script>

<style>
.easter-egg-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: transform 0.2s ease;
}

.easter-egg-container:hover {
  transform: scale(1.05);
}

.easter-egg__icon {
  font-size: 52px;
}

.easter-egg__count {
  position: absolute;
  top: -10px;
  right: -10px;
  background-color: red;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.easter-egg__menu {
  position: absolute;
  bottom: 80px;
  right: -10px;
  width: 350px;
  background-color: white;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid #e5e5e5;
}

.easter-egg__menu p {
  margin: 0 0 12px 0;
  font-weight: 600;
  color: #333;
}

.easter-egg__menu ol {
  margin: 0;
  padding-left: 20px;
  line-height: 1.6;
}

.easter-egg__menu li {
  margin-bottom: 8px;
  color: #555;
}

.easter-egg__menu li:last-child {
  margin-bottom: 0;
}
</style>