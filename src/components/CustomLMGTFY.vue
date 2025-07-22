<template>
  <div
    class="lmgtfy-container"
    :class="{
    'typing-complete': typingComplete ,
    'results-displayed': showIframe,
    }"
  >
    <!-- Google UI - show when NOT from history AND iframe is not shown -->
    <template v-if="!isFromHistory && !showIframe">
      <div class="google-heading">
        <span class="letter g1">G</span>
        <span class="letter o1">o</span>
        <span class="letter o2">o</span>
        <span class="letter g2">g</span>
        <span class="letter l">l</span>
        <span class="letter e">e</span>
      </div>
      <p class="mt-0;">Let me Google that for you</p>
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
          class="search-button fade-in"
        >
          <font-awesome-icon
            icon="arrow-pointer"
            class="pointer-icon-animate-down"
          />
          Google Search
        </button>
      </div>
    </template>

    <!-- Iframe container - show after typing is complete AND search is triggered, OR for history items -->
    <div
      v-if="showIframe"
      class="iframe-container fade-in"
    >
      <iframe
        :src="iframeUrl"
        class="research-iframe"
        frameborder="0"
        allowfullscreen
        sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
        title="Research Results"
        @load="handleIframeLoad"
      ></iframe>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from 'vue';

export default {
  name: 'CustomLMGTFY',
  props: {
    searchQuery: {
      type: String,
      required: true
    },
    isFromHistory: {
      type: Boolean,
      default: false
    }
  },
  setup(props, { emit }) {
    const searchInput = ref(null);
    const displayText = ref('');
    const typingComplete = ref(false);
    const showIframe = ref(false);
    const iframeUrl = ref('');

    // Typing animation constants
    const TYPING_SPEED = 50;
    const BATCH_SIZE = 1;

    const startTypingAnimation = () => {
      let currentIndex = 0;
      const fullText = props.searchQuery;

      const typeChar = () => {
        if (currentIndex < fullText.length) {
          displayText.value = fullText.substring(0, currentIndex + 1);
          currentIndex++;
          setTimeout(typeChar, TYPING_SPEED);
        } else {
          // Typing complete
          typingComplete.value = true;

          // Add delay before triggering search and showing iframe
          setTimeout(() => {
            handleSearch();
          }, 1500); // Reduced delay for better UX
        }
      };

      // Start typing after a brief delay
      setTimeout(typeChar, 500);
    };

    const handleSearch = () => {
      const encodedQuery = encodeURIComponent(props.searchQuery);
      const googleUrl = `https://google.gprivate.com/search.php?search?q=${encodedQuery}`;

      // Set iframe URL and show it (this will hide the Google UI)
      iframeUrl.value = googleUrl;

      // Add a small delay to make the transition smoother
      setTimeout(() => {
        showIframe.value = true;
      }, 300);
    };

    // Handle iframe load events
    const handleIframeLoad = () => {
      try {
        console.log('Iframe loaded successfully');
      } catch (error) {
        console.log('Cannot access iframe content due to CORS restrictions:', error.message);
      }
    };

    onMounted(() => {
      nextTick(() => {
        // If from history, show iframe immediately without animation
        if (props.isFromHistory) {
          typingComplete.value = true;
          handleSearch();
        } else {
          // For new research, start the typing animation
          startTypingAnimation();
        }
      });
    });

    return {
      searchInput,
      displayText,
      typingComplete,
      showIframe,
      iframeUrl,
      handleSearch,
      handleIframeLoad
    };
  }
};
</script>

<style scoped>

/* Google-styled heading */
.google-heading {
  font-size: 90px;
  font-family: 'Product Sans', Arial, sans-serif;
  font-weight: 400;
  letter-spacing: -2px;
}

.letter {
  display: inline-block;
}

.g1 {
  color: #4285f4;
}

.o1 {
  color: #ea4335;
}

.o2 {
  color: #fbbc05;
}

.g2 {
  color: #4285f4;
}

.l {
  color: #34a853;
}

.e {
  color: #ea4335;
}

/* Search container */
.search-container {
  width: 100%;
  max-width: 584px;
  margin-bottom: 30px;
  position: relative;
}

.search-input {
  position: relative;
  z-index: 10;
  width: 100%;
  height: 44px;
  border: 1px solid #dfe1e5;
  border-radius: 24px;
  padding: 0 16px;
  font-size: 16px;
  outline: none;
  transition: box-shadow 0.2s;
  background: #fff;
  color: #202124;
}

.search-input:focus {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-color: transparent;
}

/* Search button */
.button-container {
  position: relative;
  min-height: 54px;
  display: flex;
  align-items: center;
  scale: 1;
}

.results-displayed .button-container {
  scale: 0.85;
}

.pointer-icon-animate-down {
  position: absolute;
  transition: transform 2s ease;
  transform: translateY(-70px) scale(1);
  color: white;
  font-size: 24px;
}

.typing-complete .pointer-icon-animate-down {
  transform: translateY(0) scale(0.5);
}

.results-displayed .pointer-icon-animate-down {
  transform: scale(1);
}

.search-button {
  background-color: #4285f4 !important;
  border: 1px solid #f8f9fa;
  border-radius: 4px;
  color: #3c4043;
  font-family: arial, sans-serif;
  font-size: 14px;
  margin: 11px 4px;
  padding: 0 16px;
  line-height: 27px;
  height: 36px;
  min-width: 54px;
  text-align: center;
  cursor: pointer;
  user-select: none;
  transition: all 0.1s ease;
}

.search-button:hover {
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
  background-color: #f8f9fa;
  border: 1px solid #dadce0;
  color: #202124;
}

.search-button:focus {
  border: 1px solid #4285f4;
  outline: none;
}

/* Fade in animation */
.fade-in {
  animation: fadeIn 0.5s ease-in;
}

/* Enhanced fade-in animation for iframe */
.iframe-container.fade-in {
  animation: fadeInIframe 0.8s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInIframe {
  0% {
    opacity: 0;
    transform: scale(0.95);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Iframe Styles */
.iframe-container {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 800px;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  background: #fff;
  display: flex;
  justify-content: center;
  align-items: center;
}

.research-iframe {
  width: 100%;
  height: 500px;
  border: none;
  border-radius: 8px;
}

/* Update existing lmgtfy-container to accommodate iframe */
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
  width: 100%;
  position: relative;
  min-height: 500px;
  transition: min-height 0.3s ease;
}

/* Adjust height for mobile */
@media (max-width: 768px) {
  .lmgtfy-container {
    min-height: 400px;
  }
}

/* Dark theme support */
.theme-dark .lmgtfy-container {
  background: #2d2d2d;
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

.theme-dark .search-button:hover {
  background-color: #3c4043;
  border: 1px solid #5f6368;
}

.theme-dark .iframe-container {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  background: #2d2d2d;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .research-iframe {
    height: 400px;
  }
}
</style>