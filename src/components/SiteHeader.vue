<template>
  <header
    v-if="!hideHeader"
    class="site-header"
    :class="[
      `theme-${overlayTheme}`,
      ]"
    :style="variant !== 'pod' ? headerStyles : {}"
    ref="siteHeader"
  >
    <div class="site-header__container">
      <div class="site-header__logo d-flex align-center">
        <a
          href="/"
          :class="variant === 'pod' ? 'pod' : ''"
          :style="variant === 'pod' ? headerStyles : {}"
          ref="logo"
        >
          <p class="site-header__name">nickberens
            <span class="git">git:<span class="git-paren">(</span>
              <span class="git-branch">{{ gitBranch }}</span>
              <span class="git-paren">)</span>
            </span>
          </p>
          <p class="site-header__name site-header__name--mobile">nick<span class="git"><span class="git-paren">{</span>
              <span class="git-branch">berens</span>
              <span class="git-paren">}</span>
            </span>
          </p>


        </a>
        <TerminalInput
          v-if="maybeTerminalInput"
        />
      </div>

      <div class="ml-auto"/>

      <nav
        class="site-header__nav mr-4"
        :class="[variant === 'pod' ? 'pod' : '']"
        :style="variant === 'pod' ? headerStyles : {}"
        ref="nav"
      >
        <ul class="site-header__nav-list">
          <li
            v-for="item in navItemsStore"
            :key="item.url"
            class="site-header__nav-item"
          >
            <a
              :href="item.url"
              :target="item.isExternal ? '_blank' : undefined"
              :rel="item.isExternal ? 'noopener noreferrer' : undefined"
              :aria-label="item.ariaLabel"
            >
              <font-awesome-icon
                v-if="item.icon"
                size="2x"
                :icon="item.icon"
              />
              <span v-else>{{ item.text }}</span>
            </a>
          </li>
        </ul>
      </nav>
      <div
        class="site-header__mobile-nav"
        :class="{ 'is-active': isMobileMenuOpen }"
        :style="headerStyles"
      >
        <ul class="site-header__mobile-nav-list">
          <li
            v-for="item in navItemsStore"
            :key="item.url"
            class="site-header__mobile-nav-item"
          >
            <a
              :href="item.url"
              :target="item.isExternal ? '_blank' : undefined"
              :rel="item.isExternal ? 'noopener noreferrer' : undefined"
              :aria-label="item.ariaLabel"
              @click="closeMobileMenu"
            >
              <font-awesome-icon
                v-if="item.icon"
                :icon="item.icon"
              />
              <span
                v-if="item.icon"
                style="margin-left: 0.5em;"
              >{{ item.text }}</span>
              <span v-else>{{ item.text }}</span>
            </a>
          </li>
        </ul>
      </div>
      <div
        class="site-header__icons d-flex align-center"
        :class="variant === 'pod' ? 'pod' : ''"
        :style="variant === 'pod' ? headerStyles : {}"
      >
      <a
        href="/nick-ai"
        style="font-size: 2rem; text-decoration: none; position: relative;
        top: -2px;"
      >
        🤖
      </a>
      <font-awesome-icon
        :icon="['fas', 'terminal']"
        @click="toggleTerminal"
        aria-label="Toggle terminal input"
        class="terminal-icon"
      />
      <button
        class="site-header__hamburger "
        :class="[{ 'is-active': isMobileMenuOpen }]"
        @click="toggleMobileMenu"
        aria-label="Toggle menu"
      >
        🍔
      </button>
      </div>
    </div>
  </header>
</template>

<script>

import TerminalInput from './TerminalInput.vue';
import { useStore } from '@nanostores/vue';
import { navItems, isTerminalHiddenStore, isTerminalMinimizedStore } from '../stores/ui';

export default {
  name: 'SiteHeader',
  components: {
    TerminalInput,
  },
  props: {
    gitBranch: {
      type: String,
      default: 'main'
    },
    hasTerminalInput: {
      type: Boolean,
      default: false
    },
    hideHeader: {
      type: Boolean,
      default: false
    },
    variant: {
      type: String,
      default: 'default',
      validator: value => ['default', 'pod'].includes(value)
    }
  },
  data() {
    return {
      overlayTheme: 'light',
      headerBackgroundColor: 'transparent',
      isMobileMenuOpen: false,
      useTerminalInput: false,
      scrollTimeout: null,
    };
  },
  computed: {
    navItemsStore() {
      return this.navItemsStoreRaw;
    },
    headerStyles() {
      let backgroundColor = this.headerBackgroundColor;

      // Apply rgba with alpha 0.8 only for pod variant
      if (this.variant === 'pod') {
        backgroundColor = this.convertToRgba(backgroundColor, 0.2);
      }

      return {
        backgroundColor: backgroundColor,
      };
    },
    maybeTerminalInput() {
      return this.hasTerminalInput || this.useTerminalInput;
    }
  },
  setup() {
    const navItemsStoreRaw = useStore(navItems);
    const isTerminalHidden = useStore(isTerminalHiddenStore);
    const isTerminalMinimized = useStore(isTerminalMinimizedStore);
    return {
      navItemsStoreRaw,
      isTerminalHidden,
      isTerminalMinimized
    };
  },
  mounted() {
    // Ensure body scroll is enabled when component mounts
    this.isMobileMenuOpen = false;
    document.body.style.overflow = '';

    // Existing code
    window.addEventListener('scroll', this.handleScroll, { passive: true });
    this.handleScroll();
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.handleScroll);
    if (this.scrollTimeout) {
      clearTimeout(this.scrollTimeout);
    }
  },
  methods: {
    convertToRgba(color, alpha = 0.8) {
      // Handle transparent case
      if (color === 'transparent') {
        return 'transparent';
      }

      // Handle named colors
      const namedColors = {
        'white': '255, 255, 255',
        'black': '0, 0, 0',
        'red': '255, 0, 0',
        'blue': '0, 0, 255',
        'green': '0, 128, 0',
      };

      if (namedColors[color.toLowerCase()]) {
        return `rgba(${namedColors[color.toLowerCase()]}, ${alpha})`;
      }

      // Handle hex colors
      if (color.startsWith('#')) {
        const hex = color.replace('#', '');

        // Validate hex color length (must be 3 or 6 characters)
        if (hex.length !== 3 && hex.length !== 6) {
          // Return original color for invalid hex lengths
          return color;
        }

        // Validate that all characters are valid hex digits
        if (!/^[0-9A-Fa-f]+$/.test(hex)) {
          return color;
        }

        let r, g, b;

        if (hex.length === 3) {
          // Handle 3-character hex (e.g., #f00 -> #ff0000)
          r = parseInt(hex.slice(0, 1) + hex.slice(0, 1), 16);
          g = parseInt(hex.slice(1, 2) + hex.slice(1, 2), 16);
          b = parseInt(hex.slice(2, 3) + hex.slice(2, 3), 16);
        } else {
          // Handle 6-character hex (e.g., #ff0000)
          r = parseInt(hex.slice(0, 2), 16);
          g = parseInt(hex.slice(2, 4), 16);
          b = parseInt(hex.slice(4, 6), 16);
        }

        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
      }

      // Handle rgb colors - convert to rgba
      if (color.startsWith('rgb(')) {
        const rgbValues = color.match(/\d+/g);
        if (rgbValues && rgbValues.length === 3) {
          return `rgba(${rgbValues[0]}, ${rgbValues[1]}, ${rgbValues[2]}, ${alpha})`;
        }
      }

      // Handle rgba colors - update alpha
      if (color.startsWith('rgba(')) {
        const rgbaMatch = color.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)/);
        if (rgbaMatch) {
          return `rgba(${rgbaMatch[1]}, ${rgbaMatch[2]}, ${rgbaMatch[3]}, ${alpha})`;
        }
      }

      // Fallback - return original color if can't convert
      return color;
    },
    toggleTerminal() {
      // Simplified terminal toggle logic using centralized state
      if (this.isTerminalHidden) {
        // Show terminal and restore if minimized
        isTerminalHiddenStore.set(false);
        if (this.isTerminalMinimized) {
          isTerminalMinimizedStore.set(false);
        }
      } else if (this.isTerminalMinimized) {
        // Terminal is visible but minimized, so restore it
        isTerminalMinimizedStore.set(false);
      } else {
        // Terminal is visible and restored, so hide it
        isTerminalHiddenStore.set(true);
      }
    },
    toggleMobileMenu() {
      this.isMobileMenuOpen = !this.isMobileMenuOpen;
      document.body.style.overflow = this.isMobileMenuOpen ? 'hidden' : '';
    },
    closeMobileMenu() {
      this.isMobileMenuOpen = false;
      document.body.style.overflow = '';
    },
    handleScroll() {
      // Clear existing timeout
      if (this.scrollTimeout) {
        clearTimeout(this.scrollTimeout);
      }

      // Throttle the scroll handling
      this.scrollTimeout = setTimeout(() => {
        this.performScrollCheck();
      }, 16); // ~60fps
    },
    performScrollCheck() {
      const headerEl = this.$refs.siteHeader;
      if (!headerEl) return;

      const headerRect = headerEl.getBoundingClientRect();
      const checkX = window.innerWidth / 2;
      const checkY = headerRect.bottom + 10; // Check just below the header

      // Temporarily disable pointer events
      headerEl.style.pointerEvents = 'none';

      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        const elementUnder = document.elementFromPoint(checkX, checkY);
        headerEl.style.pointerEvents = 'auto';

        if (!elementUnder) {
          this.headerBackgroundColor = window.scrollY > 0 ? 'white' : 'transparent';
          this.overlayTheme = 'light';
          return;
        }

        const colorSection = elementUnder.closest('[data-section-color]');
        const themeSection = elementUnder.closest('[data-section-theme]');
        const terminalInputElement = elementUnder.closest('[data-has-terminal-input]');

        this.useTerminalInput = terminalInputElement && terminalInputElement.dataset.hasTerminalInput === 'true';

        this.headerBackgroundColor = colorSection
          ? colorSection.dataset.sectionColor
          : (window.scrollY > 0 ? 'white' : 'transparent');
        this.overlayTheme = themeSection ? themeSection.dataset.sectionTheme : 'light';

        console.log('Header background color:', this.headerBackgroundColor);
      });
    }
  }
};
</script>

<style>
.theme-dark .terminal-input:after {
  background-color: #fff;
}

.terminal-input::selection {
  background-color: white;
  color: black;
}
</style>

<style scoped>
.site-header {
  position: fixed;
  right: 0;
  left: 0;
  top: 0;
  width: 100%;
  z-index: 100;
  transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out, color 0.3s ease-in-out;
  height: var(--site-header-height);
}

.site-header__container {
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.site-header__logo {
  position: relative;
  z-index: 1002;
  color: var(--text-color, #000);
  text-decoration: none;
  height: 100%;
}

.site-header__name--mobile {
  display: none;
}

.theme-dark .site-header__logo {
  color: #fff;
}

.site-header__logo a {
  color: black;
  text-decoration: none;
}

.terminal-icon {
  cursor: pointer;
  background: black;
  color: white;
  border-radius: 8px;
  padding: 0.5rem;
  transition: color 0.3s ease;
  z-index: 1001;
}

.theme-dark .terminal-icon {
  background: #00fe01;
  color: black;
}

.theme-dark .site-header__logo a {
  color: #fff;
}

.site-header__logo p {
  margin: 0;
  font-size: clamp(1rem, 1rem + 0.5vw, 1.5rem);
  font-weight: bold;
}

.site-header__nav {
  display: block;
}

.site-header__nav-list {
  display: flex;
  align-items: center;
  list-style: none;
  margin: 0;
  padding: 0;
}

.site-header__nav-item {
  margin-left: 1.5rem;
}

.site-header__nav-item:first-child {
  margin-left: 0;
}

.site-header__nav-item a {
  text-decoration: none;
  color: inherit;
  font-weight: 500;
  transition: color 0.3s ease;
}

.site-header.theme-light .site-header__nav-item a:hover {
  color: #434343;
}

/* Hamburger Menu Button - Hidden on desktop */
.site-header__hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  z-index: 1001;
  font-size: 2rem;
  line-height: 1;
  padding: 0;
}

.site-header__icons {
  gap: .5rem;
}

.pod {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  height: 85%;
  padding: 0 1.5rem;
  border-radius: 200px;

  /* Enhanced glass effect */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 10px 15px -3px #0000004d,0 -4px 6px -2px #0000000d;
  transition: all 0.3s ease-in-out;
}

.theme-dark .pod {
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow:
    0 8px 32px 0 rgba(0, 0, 0, 0.37),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.1),
    0 1px 0 0 rgba(255, 255, 255, 0.05);

  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.05),
    rgba(255, 255, 255, 0.02)
  );
}

.site-header__hamburger.pod {
  display: none;
}

.theme-dark .pod {
  box-shadow: 0 10px 15px -3px rgba(255, 255, 255, 0.1), 0 4px 6px -4px rgba(255, 255, 255, 0.05);
}

/* Mobile Navigation */
.site-header__mobile-nav {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  background-color: #fff;
  padding-top: 80px;
  transform: translateY(-100%);
  transition: transform 0.3s ease;
  z-index: 1000;
}

@supports not (height: 100dvh) {
  .site-header__mobile-nav {
    height: 100vh;
  }
}

@supports (height: 100dvh) {
  .site-header__mobile-nav {
    height: 100dvh;
  }
}

.site-header__mobile-nav.is-active {
  transform: translateY(0);
}

.site-header__mobile-nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: center;
}

.site-header__mobile-nav-item {
  margin: 1.5rem 0;
}

.site-header__mobile-nav-item a {
  text-decoration: none;
  color: inherit;
  font-size: clamp(1.3rem, 1.3rem + 0.5vw, 1.8rem);
  transition: color 0.3s ease;
}

.site-header__mobile-nav-item a:hover {
  color: #666;
}

.site-header__hamburger.pod {
  height: 57px;
  width: 57px;
  border-radius: 50%;
  padding: 0;
}

/* Media Query for Mobile Layout */
@media (max-width: 1200px) {
  .site-header__container {
    padding: 0 1rem;
  }

  .site-header__hamburger.pod {
    display: flex;
  }

  /* Hide desktop navigation */
  .site-header__nav {
    display: none;
  }

  /* Show hamburger menu */
  .site-header__hamburger {
    display: block;
  }

  /* Show mobile navigation menu */
  .site-header__mobile-nav {
    display: block;
  }
}

@media (max-width: 768px) {
  .site-header__container {
    padding: 0 .75rem;
  }
  .pod {
    height: 65%;
    padding: 0 .75rem;
  }
  .site-header__hamburger.pod {
    height: 45px;
    width: 45px;
  }
}

@media (max-width: 600px) {
  .site-header__name {
    display: none;
  }
  .site-header__name--mobile {
    display: block;
  }
}
/* Theme-based Styling for Text */
.site-header.theme-light {
  color: #000000;
}

.site-header.theme-light .git {
  color: blue;
}

.site-header.theme-light .git-branch {
  color: red;
}

.site-header.theme-dark {
  color: #ffffff;
}

.site-header.theme-dark .git {
  color: #82aaff;
}

.site-header.theme-dark .git-branch {
  color: #ff8282;
}

.site-header.theme-dark .git-paren {
  color: #82aaff;
}

.site-header.theme-dark .git-emoji {
  color: yellow;
}

/* Hamburger animation when menu is open */
.site-header__hamburger.is-active span:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}

.site-header__hamburger.is-active span:nth-child(2) {
  opacity: 0;
}

.site-header__hamburger.is-active span:nth-child(3) {
  transform: rotate(-45deg) translate(7px, -7px);
}
</style>
