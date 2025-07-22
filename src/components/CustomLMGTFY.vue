<template>
  <div
    class="lmgtfy-container"
    :class="{
      'typing-complete': typingComplete,
      'results-displayed': showIframe,
    }"
  >
    <template v-if="!showIframe">
      <div class="google-heading">
        <span class="letter g1">G</span>
        <span class="letter o1">o</span>
        <span class="letter o2">o</span>
        <span class="letter g2">g</span>
        <span class="letter l">l</span>
        <span class="letter e">e</span>
      </div>
      <p class="mt-0">Let me Google that for you</p>
      <div class="search-container">
        <input
          ref="searchInput"
          type="text"
          class="search-input"
          :value="displayText"
          readonly
          placeholder="Search"
        />
      </div>
      <div class="button-container">
        <button
          @click="handleSearch"
          class="search-button"
          :class="{ 'fade-in': showButton }"
          :disabled="!canSearch"
        >
          <font-awesome-icon
            icon="arrow-pointer"
            class="pointer-icon"
            :class="{ 'animate-down': animatePointer }"
          />
          Google Search
        </button>
      </div>
    </template>

    <transition name="fade-in-iframe">
      <div
        v-if="showIframe"
        class="iframe-container"
      >
        <!-- Skeleton loader -->
        <div v-if="isIframeLoading" class="skeleton-loader">
          <div class="skeleton-header">
            <div class="skeleton-logo"></div>
            <div class="skeleton-search-bar"></div>
          </div>
          <div class="skeleton-content">
            <div v-for="i in 3" :key="i" class="skeleton-result">
              <div class="skeleton-result-title"></div>
              <div class="skeleton-result-url"></div>
              <div class="skeleton-result-desc">
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
              </div>
            </div>
          </div>
        </div>

        <iframe
          :src="iframeUrl"
          class="research-iframe"
          :class="{ 'loading': isIframeLoading }"
          frameborder="0"
          allowfullscreen
          sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
          title="Research Results"
          @load="handleIframeLoad"
        ></iframe>
      </div>
    </transition>
  </div>
</template>

<script>
import { ref, onMounted, nextTick, onUnmounted } from 'vue';
import { updateMessageProperty } from '../stores/ai.js';

export default {
  name: 'CustomLMGTFY',
  props: {
    searchQuery: { type: String, required: true },
    playAnimation: { type: Boolean, default: false },
    chatId: { type: String, required: true },
    messageIndex: { type: Number, required: true }
  },
  setup(props) {
    // Refs
    const searchInput = ref(null);
    const displayText = ref('');
    const typingComplete = ref(false);
    const showIframe = ref(false);
    const iframeUrl = ref('');
    const showButton = ref(!props.playAnimation);
    const animatePointer = ref(false);
    const canSearch = ref(!props.playAnimation);
    const isIframeLoading = ref(false);

    // Animation state
    let typingTimeout = null;
    let animationTimeouts = [];

    const TYPING_SPEED = 50;
    const TYPING_START_DELAY = 500;
    const BUTTON_SHOW_DELAY = 300;
    const POINTER_ANIMATION_DELAY = 100;
    const POINTER_ANIMATION_DURATION = 1200;
    const IFRAME_SHOW_DELAY = 300;

    // Clear all timeouts
    const clearAllTimeouts = () => {
      if (typingTimeout) {
        clearTimeout(typingTimeout);
        typingTimeout = null;
      }
      animationTimeouts.forEach(timeout => clearTimeout(timeout));
      animationTimeouts = [];
    };

    // Type the search query
    const typeQuery = async () => {
      return new Promise((resolve) => {
        let currentIndex = 0;
        const fullText = props.searchQuery;

        const typeChar = () => {
          if (currentIndex < fullText.length) {
            displayText.value = fullText.substring(0, currentIndex + 1);
            currentIndex++;
            typingTimeout = setTimeout(typeChar, TYPING_SPEED);
          } else {
            typingComplete.value = true;
            resolve();
          }
        };

        typingTimeout = setTimeout(typeChar, TYPING_START_DELAY);
      });
    };

    // Animate the pointer and button
    const animateSearchButton = async () => {
      return new Promise((resolve) => {
        // Show button
        showButton.value = true;

        // Start pointer animation after button appears
        const pointerTimeout = setTimeout(() => {
          animatePointer.value = true;

          // Enable search after animation completes
          const enableTimeout = setTimeout(() => {
            canSearch.value = true;
            resolve();
          }, POINTER_ANIMATION_DURATION);

          animationTimeouts.push(enableTimeout);
        }, POINTER_ANIMATION_DELAY);

        animationTimeouts.push(pointerTimeout);
      });
    };

    // Run the full animation sequence
    const runAnimationSequence = async () => {
      try {
        // Type the query
        await typeQuery();

        // Show and animate the button
        await animateSearchButton();

        // Mark animation as complete in store
        if (props.chatId != null && props.messageIndex != null) {
          updateMessageProperty(props.chatId, props.messageIndex, 'isNewResearch', false);
        }

        // Auto-search after animation
        await performSearch();
      } catch (error) {
        console.error('Animation sequence error:', error);
      }
    };

    // Perform the actual search
    const performSearch = async () => {
      const encodedQuery = encodeURIComponent(props.searchQuery);
      iframeUrl.value = `https://google.gprivate.com/search.php?search?q=${encodedQuery}`;

      // Show iframe container and start loading
      await nextTick();
      const iframeTimeout = setTimeout(() => {
        showIframe.value = true;
        isIframeLoading.value = true;
      }, IFRAME_SHOW_DELAY);

      animationTimeouts.push(iframeTimeout);
    };

    // Handle manual search button click
    const handleSearch = () => {
      if (!canSearch.value || showIframe.value) return;
      performSearch();
    };

    const handleIframeLoad = () => {
      // Add a small delay for smoother transition
      setTimeout(() => {
        isIframeLoading.value = false;
      }, 300);
    };

    // Initialize
    onMounted(() => {
      if (props.playAnimation) {
        // If animation is requested, display the query immediately for instant visual feedback
        displayText.value = props.searchQuery;
        runAnimationSequence();
      } else {
        // No animation - show everything immediately
        displayText.value = props.searchQuery;
        typingComplete.value = true;
        canSearch.value = true;

        // Immediately perform search
        nextTick(() => {
          performSearch();
        });
      }
    });

    // Cleanup
    onUnmounted(() => {
      clearAllTimeouts();
    });

    return {
      searchInput,
      displayText,
      typingComplete,
      showIframe,
      iframeUrl,
      showButton,
      animatePointer,
      canSearch,
      isIframeLoading,
      handleSearch,
      handleIframeLoad
    };
  }
};
</script>

<style scoped>
.lmgtfy-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 40px 20px;
  background: #fff;
  border-radius: 8px;
  margin: 20px 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
  min-height: 500px;
  transition: min-height 0.3s ease;
}

.google-heading {
  font-size: 90px;
  font-family: 'Product Sans', Arial, sans-serif;
  font-weight: 400;
  letter-spacing: -2px;
  margin-bottom: 20px;
}

.letter {
  display: inline-block;
}

.g1 { color: #4285f4; }
.o1 { color: #ea4335; }
.o2 { color: #fbbc05; }
.g2 { color: #4285f4; }
.l  { color: #34a853; }
.e  { color: #ea4335; }

.search-container {
  width: 100%;
  max-width: 584px;
  margin-bottom: 30px;
  position: relative;
}

.search-input {
  width: 100%;
  height: 44px;
  border: 1px solid #dfe1e5;
  border-radius: 24px;
  padding: 0 16px;
  font-size: 16px;
  background: #fff;
  color: #202124;
  transition: box-shadow 0.2s;
}

.search-input:focus {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-color: transparent;
}

.button-container {
  position: relative;
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-button {
  background-color: #f8f9fa;
  border: 1px solid #f8f9fa;
  border-radius: 4px;
  color: #3c4043;
  font-family: arial, sans-serif;
  font-size: 14px;
  margin: 11px 4px;
  padding: 0 16px;
  line-height: 27px;
  height: 36px;
  min-width: 120px;
  cursor: pointer;
  transition: all 0.1s ease;
  opacity: 0;
  transform: translateY(10px);
  position: relative;
}

.search-button.fade-in {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.search-button:hover:not(:disabled) {
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
  background-color: #f8f9fa;
  border: 1px solid #dadce0;
  color: #202124;
}

.search-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.pointer-icon {
  margin-right: 8px;
  transition: transform 1.2s ease;
  transform: translateY(-60px) scale(1.5);
  display: inline-block;
}

.pointer-icon.animate-down {
  transform: translateY(0) scale(1);
}

/* Iframe transition */
.fade-in-iframe-enter-active,
.fade-in-iframe-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.fade-in-iframe-enter-from {
  opacity: 0;
  transform: scale(0.98);
}

.fade-in-iframe-enter-to {
  opacity: 1;
  transform: scale(1);
}

.iframe-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  background: #fff;
  display: flex;
  justify-content: center;
  align-items: center;
}

.research-iframe {
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: none;
  transition: opacity 0.3s ease;
}

.research-iframe.loading {
  opacity: 0;
  position: absolute;
}

/* Skeleton Loader Styles */
.skeleton-loader {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20px;
  background: #fff;
  overflow: hidden;
}

.skeleton-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  margin-bottom: 20px;
}

.skeleton-logo {
  width: 120px;
  height: 40px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
}

.skeleton-search-bar {
  flex: 1;
  max-width: 600px;
  height: 44px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 22px;
}

.skeleton-content {
  padding: 0 20px;
}

.skeleton-result {
  margin-bottom: 30px;
}

.skeleton-result-title {
  width: 60%;
  height: 20px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-result-url {
  width: 40%;
  height: 14px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-result-desc {
  margin-bottom: 20px;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 6px;
}

.skeleton-line:first-child {
  width: 100%;
}

.skeleton-line:last-child {
  width: 80%;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Dark theme skeleton */
.theme-dark .skeleton-loader {
  background: white;
}

.theme-dark .skeleton-header {
  border-bottom-color: #ececec;
}

.theme-dark .skeleton-logo,
.theme-dark .skeleton-search-bar,
.theme-dark .skeleton-result-title,
.theme-dark .skeleton-result-url,
.theme-dark .skeleton-line {
  background: linear-gradient(90deg, #d0d0d0 25%, #c6c6c6 50%, #d0d0d0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

/* Dark theme styles */
.theme-dark .lmgtfy-container {
  background: #ffffff;
  color: #e8eaed;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.theme-dark .search-input {
  background: #303134;
  border: 1px solid #5f6368;
  color: #e8eaed;
}

.theme-dark .search-input:focus {
  border-color: #8ab4f8;
}

.theme-dark .search-button {
  background-color: #303134;
  border: 1px solid #303134;
  color: #e8eaed;
}

.theme-dark .search-button:hover:not(:disabled) {
  background-color: #3c4043;
  border: 1px solid #5f6368;
}

.theme-dark .iframe-container {
  background: #2d2d2d;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

/* Responsive styles */
@media (max-width: 768px) {
  .lmgtfy-container {
    min-height: 400px;
    padding: 20px 10px;
  }

  .google-heading {
    font-size: 60px;
  }

  .research-iframe {
    min-height: 400px;
  }
}
</style>