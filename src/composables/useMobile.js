// composables/useMobile.js
import { ref, onMounted, onUnmounted } from 'vue';

const MOBILE_BREAKPOINT = 768;

export function useMobile(breakpoint = MOBILE_BREAKPOINT) {
  const isMobile = ref(false); // Default to false for SSR compatibility
  const isMounted = ref(false); // Track if component is mounted to prevent layout shift

  const updateMobileState = () => {
    isMobile.value = window.innerWidth <= breakpoint;
  };

  onMounted(() => {
    // Set initial state after mount when window is available
    updateMobileState();
    isMounted.value = true;
    window.addEventListener('resize', updateMobileState);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', updateMobileState);
  });

  return { isMobile, isMounted };
}
