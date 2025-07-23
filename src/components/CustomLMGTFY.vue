<template>
  <div
    class="lmgtfy-container"
    :class="{
      'typing-complete': typingComplete,
      'results-displayed': showIframe,
      'button-visible': showButton,
      'pointer-animating': animatePointer,
      'letters-bouncing': lettersBouncing,
      'search-loading': isIframeLoading
    }"
  >
    <div class="google-container">
      <div class="google-heading">
        <span
          v-for="(letter, index) in letters"
          :key="index"
          class="letter"
          :class="letter.class"
        >
          {{ letter.char }}
        </span>
      </div>

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

      <p class="mt-0 font-bold text-center" style="color: red;">
        Let me Google that for you.
      </p>

      <div class="button-container">
        <button
          @click="handleSearch"
          class="search-button"
          :disabled="!canSearch"
        >
          <span class="pointer-icon-container">
            <font-awesome-icon icon="arrow-pointer" class="pointer-icon" />
            <font-awesome-icon icon="arrow-pointer" class="pointer-icon pointer-icon-shadow" />
          </span>
          Google Search
        </button>
      </div>
    </div>

    <transition name="fade-in-iframe">
      <div v-if="showIframe" class="iframe-container">
        <!-- Skeleton loader -->
        <div v-if="isIframeLoading" class="skeleton-loader">
          <div class="skeleton-header">
            <div class="skeleton-logo"></div>
            <div class="skeleton-search-bar"></div>
          </div>
          <div class="skeleton-content">
            <div
              v-for="i in 3"
              :key="i"
              class="skeleton-result"
            >
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
          v-if="showIframe"
          :src="iframeUrl"
          class="research-iframe"
          frameborder="0"
          allowfullscreen
          sandbox="allow-scripts allow-forms allow-popups"
          title="Research Results"
          @load="handleIframeLoad"
          @error="handleIframeError"
        />
      </div>
    </transition>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick, onUnmounted } from 'vue'
import { updateMessageProperty } from '../stores/ai.js'

export default {
  name: 'CustomLMGTFY',
  props: {
    searchQuery: { type: String, required: true },
    playAnimation: { type: Boolean, default: false },
    chatId: { type: String, required: true },
    messageIndex: { type: Number, required: true }
  },
  emits: ['height-changed'],

  setup(props, { emit }) {
    // Simple helper
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

    // Reactive state (instead of DOM queries)
    const letters = reactive([
      { char: 'G', class: 'g1' },
      { char: '🙄', class: 'o1' },
      { char: '🙄', class: 'o2' },
      { char: 'g', class: 'g2' },
      { char: 'l', class: 'l' },
      { char: 'e', class: 'e' }
    ])

    // Animation state - centralized on root element
    const displayText = ref('')
    const typingComplete = ref(false)
    const showIframe = ref(false)
    const iframeUrl = ref('')
    const showButton = ref(!props.playAnimation)
    const animatePointer = ref(false)
    const lettersBouncing = ref(false)
    const canSearch = ref(!props.playAnimation)
    const isIframeLoading = ref(false)

    // Animation methods (separate from config)
    const animationMethods = {
      animateGoogleLogo: async (config) => {
        lettersBouncing.value = true

        // Let CSS handle the visual animation, we just control timing
        await sleep(config.duration + (config.staggerDelay * letters.length))

        lettersBouncing.value = false
      },

      typeQuery: async (config) => {
        const maxLength = 30
        const text = props.searchQuery.length > maxLength
          ? props.searchQuery.substring(0, maxLength) + '...'
          : props.searchQuery

        let currentText = ''
        for (const char of text) {
          currentText += char
          displayText.value = currentText
          await sleep(config.speed)
        }
        typingComplete.value = true
      },

      showButton: async (config) => {
        showButton.value = true
        await sleep(config.duration)
      },

      animatePointer: async (config) => {
        animatePointer.value = true
        await sleep(config.duration)
        canSearch.value = true
      },

      performSearch: async (config) => {
        const encodedQuery = encodeURIComponent(props.searchQuery)
        iframeUrl.value = `https://google.gprivate.com/search.php?search?q=${encodedQuery}`

        await sleep(config.delay)
        showIframe.value = true
        isIframeLoading.value = true

        await nextTick()
        emit('height-changed')
      },

      showTextInstantly: async () => {
        const maxLength = 30
        displayText.value = props.searchQuery.length > maxLength
          ? props.searchQuery.substring(0, maxLength) + '...'
          : props.searchQuery
        typingComplete.value = true
      },

      enableSearch: async (config) => {
        showButton.value = true
        canSearch.value = true
        await sleep(config.delay)
      },

      runLogoAndTypingParallel: async () => {
        await Promise.all([
          animationMethods.animateGoogleLogo({ duration: 600, staggerDelay: 150 }),
          animationMethods.typeQuery({ speed: 150 })
        ])
      }
    }

    // Animation config - clean and focused on timing/sequencing
    const animationSequence = [
      {
        name: 'typing',
        delay: 300,
        speed: 150,
        action: 'typeQuery'
      },
      {
        name: 'logo-bounce',
        delay: 200,
        duration: 600,
        staggerDelay: 150,
        action: 'animateGoogleLogo'
      },
      {
        name: 'show-button',
        delay: 100,
        duration: 300,
        action: 'showButton'
      },
      {
        name: 'animate-pointer',
        delay: 100,
        duration: 3500,
        action: 'animatePointer'
      },
      {
        name: 'perform-search',
        delay: 200,
        action: 'performSearch'
      }
    ]

    // Fast sequence (no animations)
    const fastSequence = [
      {
        name: 'show-text',
        action: 'showTextInstantly'
      },
      {
        name: 'enable-search',
        delay: 100,
        action: 'enableSearch'
      },
      {
        name: 'perform-search',
        delay: 200,
        action: 'performSearch'
      }
    ]

    // Simple animation runner
    const runAnimations = async (sequence) => {
      for (const animation of sequence) {
        await sleep(animation.delay || 0)
        await animationMethods[animation.action](animation)
      }

      // Update store when complete
      if (props.chatId !== null && props.messageIndex != null) {
        updateMessageProperty(props.chatId, props.messageIndex, 'isNewResearch', false)
      }

      await nextTick()
      emit('height-changed')
    }

    // Easy sequence variations
    const createSlowSequence = () => {
      return animationSequence.map(anim => {
        if (anim.name === 'typing') return { ...anim, speed: 300 }
        if (anim.name === 'logo-bounce') return { ...anim, staggerDelay: 300 }
        return anim
      })
    }

    const createParallelSequence = () => {
      // Run logo and typing at the same time
      return [
        {
          name: 'logo-and-typing',
          delay: 200,
          action: 'runLogoAndTypingParallel'
        },
        ...animationSequence.slice(2) // rest of the animations
      ]
    }

    // Event handlers
    const handleSearch = () => {
      if (!canSearch.value || showIframe.value) return

      const searchOnly = [{
        name: 'perform-search',
        delay: 0,
        action: 'performSearch'
      }]

      runAnimations(searchOnly)
    }

    const handleIframeLoad = () => {
      setTimeout(() => {
        isIframeLoading.value = false
        console.info('The iframe error is expected 🙄')
        nextTick(() => emit('height-changed'))
      }, 300)
    }

    const handleIframeError = () => {
      isIframeLoading.value = false
      console.error('Failed to load search results')
    }

    // Initialize
    onMounted(() => {
      if (props.playAnimation) {
        displayText.value = ''
        runAnimations(animationSequence)
      } else {
        runAnimations(fastSequence)
      }
    })

    return {
      letters,
      displayText,
      typingComplete,
      showIframe,
      iframeUrl,
      showButton,
      animatePointer,
      lettersBouncing,
      canSearch,
      isIframeLoading,
      handleSearch,
      handleIframeLoad,
      handleIframeError,

      // For debugging/testing
      runSlowAnimations: () => runAnimations(createSlowSequence()),
      runParallelAnimations: () => runAnimations(createParallelSequence())
    }
  }
}
</script>

<style scoped>
/* =============================================================================
   ANIMATION KEYFRAMES
   ============================================================================= */

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-20px); }
  60% { transform: translateY(-10px); }
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* =============================================================================
   BASE COMPONENT STYLES
   ============================================================================= */

.lmgtfy-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  margin: 20px 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
  min-height: 400px;
}

.google-container {
  position: relative;
  padding: 20px 10px;
  z-index: 20;
  margin-bottom: -120px;
  background: #fff;
  width: 100%;
}

.google-heading {
  font-size: 90px;
  font-family: 'Product Sans', Arial, sans-serif;
  font-weight: 400;
  letter-spacing: -2px;
  margin-bottom: 20px;
  text-align: center;
}

.letter {
  display: inline-block;
}

/* Letter Colors (Base Styles Only) */
.g1 { color: #4285f4; }
.o1 { color: #ea4335; }
.o2 { color: #fbbc05; }
.g2 { color: #4285f4; }
.l { color: #34a853; }
.e { color: #ea4335; }

.search-container {
  width: 100%;
  max-width: 584px;
  margin-bottom: 30px;
  margin-left: auto;
  margin-right: auto;
  position: relative;
}

.search-input {
  position: relative;
  width: 100%;
  height: 44px;
  border: 1px solid #676767;
  border-radius: 24px;
  padding: 0 16px;
  font-size: 16px;
  background: #fff;
  color: #202124;
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
  position: relative;
  background-color: #4285f4;
  border-radius: 4px;
  border: none;
  color: white;
  font-family: arial, sans-serif;
  font-size: 14px;
  margin: 11px 4px;
  padding: 0 16px;
  line-height: 27px;
  height: 36px;
  min-width: 120px;
  cursor: pointer;
  opacity: 0; /* Default hidden state */
}

.search-button:hover:not(:disabled) {
  background-color: #3367d6;
}

.search-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.pointer-icon-container {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  transform: translate(-90px, -120px); /* Default hidden position */
}

.pointer-icon {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 10;
  color: black;
  display: inline-block;
  font-size: 24px;
}

.pointer-icon-shadow {
  left: -1px;
  top: 1px;
  z-index: 5;
  transform: scale(1.1);
  color: white;
}

.iframe-container {
  position: relative;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.research-iframe {
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: none;
}

.iframe-container::before {
  content: '';
  display: block;
  position: absolute;
  z-index: 10;
  top: 0;
  left: 0;
  right: 0;
  height: 82px;
  background: white;
  margin-bottom: -100px;
}

/* Skeleton Loader Styles */
.skeleton-loader {
  position: absolute;
  width: 100%;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20px;
  background: #fff;
  overflow: hidden;
}

.skeleton-loader * {
  width: 100%;
}

.skeleton-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  margin-bottom: 20px;
  width: 100%;
}

.skeleton-logo {
  width: 120px;
  height: 40px;
  border-radius: 4px;
}

.skeleton-search-bar {
  flex: 1;
  max-width: 600px;
  height: 44px;
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
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-result-url {
  width: 40%;
  height: 14px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-result-desc {
  margin-bottom: 20px;
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  margin-bottom: 6px;
}

.skeleton-line:first-child {
  width: 100%;
}

.skeleton-line:last-child {
  width: 80%;
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

@media (max-width: 450px) {
  .google-heading {
    font-size: 40px;
  }
}

/* =============================================================================
   ANIMATION STATES (Modifications to Base Styles)
   ============================================================================= */

/* Button Visibility */
.lmgtfy-container.button-visible .search-button {
  opacity: 1;
  transition: opacity 0.3s ease;
}

/* Pointer Animation */
.lmgtfy-container.pointer-animating .pointer-icon-container {
  transform: translateY(0);
  transition: transform 3s ease;
}

/* Letter Bouncing */
.lmgtfy-container.letters-bouncing .letter:nth-child(1) {
  animation: bounce 0.6s ease-in-out;
  animation-delay: 0ms;
}

.lmgtfy-container.letters-bouncing .letter:nth-child(2) {
  animation: bounce 0.6s ease-in-out;
  animation-delay: 150ms;
}

.lmgtfy-container.letters-bouncing .letter:nth-child(3) {
  animation: bounce 0.6s ease-in-out;
  animation-delay: 300ms;
}

.lmgtfy-container.letters-bouncing .letter:nth-child(4) {
  animation: bounce 0.6s ease-in-out;
  animation-delay: 450ms;
}

.lmgtfy-container.letters-bouncing .letter:nth-child(5) {
  animation: bounce 0.6s ease-in-out;
  animation-delay: 600ms;
}

.lmgtfy-container.letters-bouncing .letter:nth-child(6) {
  animation: bounce 0.6s ease-in-out;
  animation-delay: 750ms;
}

/* Loading Animation */
.lmgtfy-container.search-loading .skeleton-logo,
.lmgtfy-container.search-loading .skeleton-search-bar,
.lmgtfy-container.search-loading .skeleton-result-title,
.lmgtfy-container.search-loading .skeleton-result-url,
.lmgtfy-container.search-loading .skeleton-line {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

/* Vue Transition Classes */
.fade-in-iframe-enter-active,
.fade-in-iframe-leave-active {
  transition: opacity 0.3s ease;
}

.fade-in-iframe-enter-from,
.fade-in-iframe-leave-to {
  opacity: 0;
}
</style>