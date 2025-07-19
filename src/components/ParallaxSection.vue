<template>
  <section
    class="parallax-section"
    :class="{
      'parallax-section--full-width': fullWidth,
      'parallax-section--no-padding': noPadding
    }"
    :style="{ backgroundColor }"
    ref="sectionRef"
  >
    <!-- Background layer -->
    <div
      class="parallax-section__background"
      ref="backgroundRef"
      :style="{ transform: `translateY(${currentOffset}px)` }"
    >
      <img
        :src="backgroundImage"
        :alt="backgroundAlt"
        class="parallax-section__bg-image"
      />
    </div>

    <!-- Foreground content -->
    <div class="parallax-section__content">
      <img
        :src="foregroundImage"
        :alt="foregroundAlt"
        class="parallax-section__fg-image"
        :class="{ 'floating': floatingForeground }"
      />
    </div>
  </section>
</template>

<script>
export default {
  name: 'ParallaxSection',
  props: {
    backgroundColor: { type: String, default: 'transparent' },
    backgroundImage: { type: String, required: true },
    foregroundImage: { type: String, required: true },
    backgroundAlt: { type: String, default: 'Background image' },
    foregroundAlt: { type: String, default: 'Foreground image' },
    fullWidth: { type: Boolean, default: false },
    noPadding: { type: Boolean, default: false },
    parallaxSpeed: { type: Number, default: 0.5 },
    foregroundMaxWidth: { type: String, default: '300px' },
    foregroundMaxWidthMobile: { type: String, default: '200px' },
    floatingForeground: { type: Boolean, default: false },
  },
  data() {
    return {
      currentOffset: 0,
      inViewport: false,
      isScrolling: false,
      ticking: false
    };
  },
  mounted() {
    document.addEventListener('scroll', this.onScroll, { passive: true });
    window.addEventListener('resize', this.onResize, { passive: true });

    this.$nextTick(() => {
      setTimeout(() => {
        this.calculateParallax();
      }, 100);
    });
  },
  beforeUnmount() {
    document.removeEventListener('scroll', this.onScroll);
    window.removeEventListener('resize', this.onResize);
  },
  methods: {
    onScroll() {
      this.isScrolling = true;
      if (!this.ticking) {
        requestAnimationFrame(() => {
          this.calculateParallax();
          this.ticking = false;
          setTimeout(() => {
            this.isScrolling = false;
          }, 100);
        });
        this.ticking = true;
      }
    },
    onResize() {
      this.calculateParallax();
    },
    calculateParallax() {
      const el = this.$refs.sectionRef;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;

      this.inViewport = rect.top < vh && rect.bottom > 0;
      if (this.inViewport) {
        const elementCenter = rect.top + rect.height / 2;
        const viewportCenter = vh / 2;
        const distance = elementCenter - viewportCenter;
        this.currentOffset = distance * this.parallaxSpeed * -0.3;
      }
    }
  }
};
</script>

<style scoped>
.parallax-section {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem 1.5rem;
  overflow: hidden;
  min-height: 100vh;
}

.parallax-section--full-width {
  padding: 4rem 0;
}

.parallax-section--no-padding {
  padding: 0;
}

.parallax-section__background {
  position: absolute;
  top: -20%;
  left: 0;
  right: 0;
  bottom: -20%;
  z-index: 1;
  height: 140%;
  width: 100%;
  overflow: hidden;
  will-change: transform;
}

.parallax-section__bg-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.parallax-section__content {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 100%;
}

.parallax-section__fg-image {
  max-width: v-bind(foregroundMaxWidth);
  width: 100%;
  margin: 0 auto;
  height: auto;
  display: block;
  position: relative;
  z-index: 3;
}

/* Floating animation */
@keyframes float {
  0% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-30px);
  }
  100% {
    transform: translateY(0px);
  }
}

.floating {
  animation: float 3s ease-in-out infinite;
  will-change: transform;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .parallax-section__fg-image {
    max-width: v-bind(foregroundMaxWidthMobile);
  }
  /*.parallax-section__background {
    top: 0;
    bottom: 0;
    height: 100%;
    transform: none !important;
  }*/
}
</style>
