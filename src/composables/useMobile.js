// composables/useMobile.js
import { ref, onMounted, onUnmounted } from 'vue';

const MOBILE_BREAKPOINT = 768;

export function useMobile(breakpoint = MOBILE_BREAKPOINT) {
  const isMobile = ref(window.innerWidth < breakpoint);

  const updateMobileState = () => {
    isMobile.value = window.innerWidth < breakpoint;
  };

  onMounted(() => {
    window.addEventListener('resize', updateMobileState);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', updateMobileState);
  });

  return { isMobile };
}