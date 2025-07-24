<template>
  <div
    class="lmgtfy-container"
    :class="{
      'typing-complete': typingComplete,
      'results-displayed': showIframe,
      'button-visible': showButtonVisible,
      'pointer-animating': pointerAnimating,
      'letters-bouncing': lettersBouncing,
      'search-loading': isIframeLoading,
      'animate-button-click': buttonClickAnimating,
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
          v-if="showIframe"
          :src="iframeUrl"
          class="research-iframe"
          frameborder="0"
          allowfullscreen
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          title="Research Results"
          @load="handleIframeLoad"
          @error="handleIframeError"
        />
      </div>
    </transition>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
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
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

    // === Centralized Animation Configuration ===
    const animationConfig = {
      typingSpeedMs: ref(150),
      logoBounceBaseMs: ref(600),
      logoBounceStaggerMs: ref(150),
      showButtonDelayMs: ref(300),
      buttonClickDurationMs: ref(300),
      pointerSpeedMs: ref(3000),
      buttonFadeMs: ref(300),
      bounceAnimationMs: ref(600),
      skeletonLoopMs: ref(1500),
      iframeFadeMs: ref(300),
      buttonScaleMs: ref(300),
      iframeLoadDelayMs: ref(600) // Increased from 300ms to 600ms
    }

    // CSS bindings - computed properties for dynamic CSS
    const typingSpeedCss = computed(() => `${animationConfig.typingSpeedMs.value}ms`)
    const pointerSpeedCss = computed(() => `${animationConfig.pointerSpeedMs.value}ms`)
    const buttonFadeCss = computed(() => `${animationConfig.buttonFadeMs.value}ms`)
    const bounceAnimationCss = computed(() => `${animationConfig.bounceAnimationMs.value}ms`)
    const skeletonLoopCss = computed(() => `${animationConfig.skeletonLoopMs.value}ms`)
    const iframeFadeCss = computed(() => `${animationConfig.iframeFadeMs.value}ms`)
    const buttonScaleCss = computed(() => `${animationConfig.buttonScaleMs.value}ms`)

    const letters = reactive([
      { char: 'G', class: 'g1' },
      { char: '🙄', class: 'o1' },
      { char: '🙄', class: 'o2' },
      { char: 'g', class: 'g2' },
      { char: 'l', class: 'l' },
      { char: 'e', class: 'e' }
    ])

    const displayText = ref('')
    const typingComplete = ref(false)
    const showIframe = ref(false)
    const iframeUrl = ref('')
    const showButtonVisible = ref(!props.playAnimation)
    const pointerAnimating = ref(false)
    const buttonClickAnimating = ref(false)
    const lettersBouncing = ref(false)
    const canSearch = ref(!props.playAnimation)
    const isIframeLoading = ref(false)

    const logoBounceTotalMs = computed(() =>
      animationConfig.logoBounceBaseMs.value + animationConfig.logoBounceStaggerMs.value * letters.length
    )

    // === Animation functions ===
    const typeQuery = async (speed = animationConfig.typingSpeedMs.value) => {
      const maxLength = 30
      const text =
        props.searchQuery.length > maxLength
          ? props.searchQuery.substring(0, maxLength) + '...'
          : props.searchQuery

      displayText.value = ''
      for (const char of text) {
        displayText.value += char
        await sleep(speed)
      }
      typingComplete.value = true
    }

    const animateGoogleLogo = () => { lettersBouncing.value = true }
    const showButton = () => { showButtonVisible.value = true }
    const animatePointer = () => { pointerAnimating.value = true; canSearch.value = true }
    const animateButtonClick = async () => {
      buttonClickAnimating.value = true
      // Reset the animation state after the duration to return to normal scale
      setTimeout(() => {
        buttonClickAnimating.value = false
      }, animationConfig.buttonClickDurationMs.value)
    }
    const performSearch = async () => {
      const encodedQuery = encodeURIComponent(props.searchQuery)
      iframeUrl.value = `https://google.gprivate.com/search.php?search?q=${encodedQuery}`
      await nextTick()
      setTimeout(() => {
        showIframe.value = true
        isIframeLoading.value = true
      }, animationConfig.buttonClickDurationMs.value + 300)
      await nextTick()
      emit('height-changed')
    }

    const showTextInstantly = () => {
      const maxLength = 30
      displayText.value =
        props.searchQuery.length > maxLength
          ? props.searchQuery.substring(0, maxLength) + '...'
          : props.searchQuery
      typingComplete.value = true
    }
    const enableSearchInstantly = () => {
      showButtonVisible.value = true
      canSearch.value = true
    }

    // === Timeline with dynamic speed refs ===
    const createNormalTimeline = () => [
      { step: () => typeQuery(animationConfig.typingSpeedMs.value), delay: 0 },
      { step: () => animateGoogleLogo(), delay: logoBounceTotalMs.value },
      { step: () => showButton(), delay: animationConfig.showButtonDelayMs.value },
      { step: () => animatePointer(), delay: animationConfig.pointerSpeedMs.value + 500 },
      { step: () => animateButtonClick(), delay: animationConfig.buttonClickDurationMs.value },
      { step: () => performSearch(), delay: 0 }
    ]

    const createFastTimeline = () => [
      { step: () => showTextInstantly(), delay: 0 },
      { step: () => enableSearchInstantly(), delay: 0 },
      { step: () => animateButtonClick(), delay: animationConfig.buttonClickDurationMs.value },
      { step: () => performSearch(), delay: 0 }
    ]

    const runTimeline = async (timeline) => {
      for (const { step, delay } of timeline) {
        await step()
        if (delay) await sleep(delay)
      }
      if (props.chatId && props.messageIndex != null) {
        updateMessageProperty(props.chatId, props.messageIndex, 'isNewResearch', false)
      }
      await nextTick()
      emit('height-changed')
    }

    const handleSearch = () => {
      if (!canSearch.value || showIframe.value) return
      runTimeline([{ step: () => performSearch(), delay: 0 }])
    }

    const handleIframeLoad = () => {
      // Give extra time for stylesheets to load and render
      const checkStylesLoaded = () => {
        setTimeout(() => {
          isIframeLoading.value = false
          nextTick(() => emit('height-changed'))
        }, animationConfig.iframeLoadDelayMs.value)
      }

      // Double-check after a longer delay to ensure styles are rendered
      setTimeout(checkStylesLoaded, 100)
    }

    const handleIframeError = () => {
      isIframeLoading.value = false
      console.error('Failed to load search results')
    }

    onMounted(() => {
      displayText.value = ''
      const timeline = props.playAnimation ? createNormalTimeline() : createFastTimeline()
      runTimeline(timeline)
    })

    return {
      letters,
      displayText,
      typingComplete,
      showIframe,
      iframeUrl,
      showButtonVisible,
      pointerAnimating,
      buttonClickAnimating,
      lettersBouncing,
      canSearch,
      isIframeLoading,
      // CSS binding computed properties
      pointerSpeedCss,
      buttonFadeCss,
      bounceAnimationCss,
      skeletonLoopCss,
      iframeFadeCss,
      buttonScaleCss,
      handleSearch,
      handleIframeLoad,
      handleIframeError
    }
  }
}
</script>

<style scoped>
@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-20px); }
  60% { transform: translateY(-10px); }
}
@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

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
.letter { display: inline-block; }
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
  transition: transform v-bind(buttonScaleCss) ease;
}
.search-button {
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
  opacity: 0;
  transition: opacity v-bind(buttonFadeCss) ease;
}
.search-button:hover:not(:disabled) { background-color: #3367d6; }
.search-button:disabled { cursor: not-allowed; opacity: 0.6; }

.pointer-icon-container {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  transform: translate(-90px, -120px);
  transition: transform v-bind(pointerSpeedCss) ease;
}
.pointer-icon {
  position: absolute; left: 0; top: 0; z-index: 10; color: black; font-size: 24px;
}
.pointer-icon-shadow { left: -1px; top: 1px; z-index: 5; transform: scale(1.1); color: white; }

.iframe-container {
  position: relative;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.research-iframe { width: 100%; height: 100%; min-height: 500px; border: none; }
.iframe-container::before {
  content: ''; position: absolute; z-index: 10; top: 0; left: 0; right: 0; height: 82px; background: white;
  margin-bottom: -100px;
}

.skeleton-loader { position: absolute; width: 100%; padding: 20px; background: #fff; overflow: hidden; }
.skeleton-header {
  display: flex; align-items: center; gap: 20px; padding: 20px; border-bottom: 1px solid #e0e0e0;
  margin-bottom: 20px; width: 100%;
}
.skeleton-logo { width: 120px; height: 40px; border-radius: 4px; }
.skeleton-search-bar { flex: 1; max-width: 600px; height: 44px; border-radius: 22px; }
.skeleton-content { padding: 0 20px; }
.skeleton-result { margin-bottom: 30px; }
.skeleton-result-title { width: 60%; height: 20px; border-radius: 4px; margin-bottom: 8px; }
.skeleton-result-url { width: 40%; height: 14px; border-radius: 4px; margin-bottom: 8px; }
.skeleton-result-desc { margin-bottom: 20px; }
.skeleton-line { height: 14px; border-radius: 4px; margin-bottom: 6px; }
.skeleton-line:first-child { width: 100%; }
.skeleton-line:last-child { width: 80%; }

@media (max-width: 768px) {
  .lmgtfy-container { min-height: 400px; padding: 20px 10px; }
  .google-heading { font-size: 60px; }
  .research-iframe { min-height: 400px; }
}
@media (max-width: 450px) {
  .google-heading { font-size: 40px; }
}

.lmgtfy-container.button-visible .search-button {
  opacity: 1;
}
.lmgtfy-container.pointer-animating .pointer-icon-container { transform: translate(0, 0); }
.lmgtfy-container.letters-bouncing .letter:nth-child(1) { animation: bounce v-bind(bounceAnimationCss) ease-in-out; animation-delay: 0ms; }
.lmgtfy-container.letters-bouncing .letter:nth-child(2) { animation: bounce v-bind(bounceAnimationCss) ease-in-out; animation-delay: 150ms; }
.lmgtfy-container.letters-bouncing .letter:nth-child(3) { animation: bounce v-bind(bounceAnimationCss) ease-in-out; animation-delay: 300ms; }
.lmgtfy-container.letters-bouncing .letter:nth-child(4) { animation: bounce v-bind(bounceAnimationCss) ease-in-out; animation-delay: 450ms; }
.lmgtfy-container.letters-bouncing .letter:nth-child(5) { animation: bounce v-bind(bounceAnimationCss) ease-in-out; animation-delay: 600ms; }
.lmgtfy-container.letters-bouncing .letter:nth-child(6) { animation: bounce v-bind(bounceAnimationCss) ease-in-out; animation-delay: 750ms; }
.lmgtfy-container.animate-button-click .button-container { transform: scale(0.95); }
.lmgtfy-container.search-loading .skeleton-logo,
.lmgtfy-container.search-loading .skeleton-search-bar,
.lmgtfy-container.search-loading .skeleton-result-title,
.lmgtfy-container.search-loading .skeleton-result-url,
.lmgtfy-container.search-loading .skeleton-line {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0f0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading v-bind(skeletonLoopCss) infinite;
}
.fade-in-iframe-enter-active, .fade-in-iframe-leave-active {
  transition: opacity v-bind(iframeFadeCss) ease;
}
.fade-in-iframe-enter-from, .fade-in-iframe-leave-to { opacity: 0; }
</style>