<template>
  <header
    v-if="!hideHeader"
    class="site-header"
    :class="[
      `theme-${overlayTheme}`,
      variant === 'mobile-condensed' ? 'site-header--mobile-condensed' : '',
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
              <span class="git-branch">
                <font-awesome-icon
                  icon="house-chimney"
                  class="base-icon"
                />
              </span>
              <span class="git-paren">)</span>
            </span>
          </p>
          <p class="site-header__name site-header__name--mobile">nick:<span class="git"><span class="git-paren">(</span>
              <span class="git-branch"><font-awesome-icon
                icon="house-chimney"
                class="base-icon"
              /></span>
              <span class="git-paren">)</span>
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
            :class="{ 'has-dropdown': item.hasDropdown }"
          >
            <a
              v-if="!item.hasDropdown"
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

            <!-- Dropdown Menu -->
            <div v-if="item.hasDropdown" class="dropdown">
              <button
                class="dropdown-toggle"
                @click="toggleDropdown(item.text)"
                :aria-expanded="isDropdownOpen(item.text)"
              >
                <span>{{ item.text }}</span>
                <font-awesome-icon
                  :icon="['fas', 'chevron-down']"
                  :class="{ 'rotated': isDropdownOpen(item.text) }"
                  class="dropdown-arrow"
                />
              </button>
              <ul
                v-if="isDropdownOpen(item.text)"
                class="dropdown-menu"
                :style="dropdownStyles"
              >
                <li v-if="!item.dropdownItems || item.dropdownItems.length === 0" class="dropdown-item">
                  <span>No fonts available</span>
                </li>
                <li
                  v-for="subItem in item.dropdownItems"
                  :key="subItem.url"
                  class="dropdown-item"
                >
                  <a
                    :href="subItem.url"
                    @click="closeAllDropdowns"
                  >
                    {{ subItem.text }}
                  </a>
                </li>
              </ul>
            </div>
          </li>
        </ul>
      </nav>
      <div
        class="site-header__mobile-nav"
        :class="{ 'is-active': isMobileMenuOpen }"
        :style="headerStyles"
      >
        <button
          class="site-header__mobile-nav-close"
          @click="closeMobileMenu"
          aria-label="Close menu"
        >
          <font-awesome-icon :icon="['fas', 'times']"/>
        </button>
        <ul class="site-header__mobile-nav-list">
          <li
            v-for="item in navItemsStore"
            :key="item.url"
            class="site-header__mobile-nav-item"
          >
            <!-- Regular nav items -->
            <a
              v-if="!item.hasDropdown"
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

            <!-- Mobile dropdown items -->
            <div v-if="item.hasDropdown" class="mobile-dropdown">
              <button
                class="mobile-dropdown-toggle"
                @click="toggleMobileDropdown(item.text)"
              >
                <span>{{ item.text }}</span>
                <font-awesome-icon
                  :icon="['fas', 'chevron-down']"
                  :class="{ 'rotated': isMobileDropdownOpen(item.text) }"
                  class="dropdown-arrow"
                />
              </button>
              <ul
                v-if="isMobileDropdownOpen(item.text)"
                class="mobile-dropdown-menu"
              >
                <li v-if="!item.dropdownItems || item.dropdownItems.length === 0" class="mobile-dropdown-item">
                  <span style="color: #666;">No fonts available</span>
                </li>
                <li
                  v-for="subItem in item.dropdownItems"
                  :key="subItem.url"
                  class="mobile-dropdown-item"
                >
                  <a
                    :href="subItem.url"
                    @click="closeMobileMenu"
                  >
                    {{ subItem.text }}
                  </a>
                </li>
              </ul>
            </div>
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
          class="ai-icon"
        >
          <img
            :src="aiIconSvg"
            alt="AI Icon"
            style="width: 34px;"
          />
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
import aiIconSvg from '../assets/svg/ai-icon.svg?url';

import { navItems } from '../stores/ui';
import {
  isTerminalHiddenStore,
  isTerminalMinimizedStore
} from '../stores/terminal-window';

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
      validator: value => ['default', 'pod', 'mobile-condensed'].includes(value)
    }
  },
  data() {
    return {
      overlayTheme: 'light',
      headerBackgroundColor: 'transparent',
      isMobileMenuOpen: false,
      useTerminalInput: false,
      scrollTimeout: null,
      aiIconSvg,
      openDropdowns: new Set(),
      openMobileDropdowns: new Set(),
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
    dropdownStyles() {
      let backgroundColor = this.headerBackgroundColor;

      // Apply transparency for glass effect
      backgroundColor = this.convertToRgba(backgroundColor, 0.9);

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

    // Re-run theme detection on page navigation (for view transitions)
    document.addEventListener('astro:page-load', this.performScrollCheck);

    // Close dropdowns when clicking outside
    document.addEventListener('click', this.handleClickOutside);
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.handleScroll);
    document.removeEventListener('astro:page-load', this.performScrollCheck);
    document.removeEventListener('click', this.handleClickOutside);
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
      this.openMobileDropdowns.clear();
      document.body.style.overflow = '';
    },
    toggleDropdown(itemText) {
      if (this.openDropdowns.has(itemText)) {
        this.openDropdowns.delete(itemText);
      } else {
        this.openDropdowns.clear();
        this.openDropdowns.add(itemText);
      }
    },
    toggleMobileDropdown(itemText) {
      if (this.openMobileDropdowns.has(itemText)) {
        this.openMobileDropdowns.delete(itemText);
      } else {
        this.openMobileDropdowns.clear();
        this.openMobileDropdowns.add(itemText);
      }
    },
    isDropdownOpen(itemText) {
      return this.openDropdowns.has(itemText);
    },
    isMobileDropdownOpen(itemText) {
      return this.openMobileDropdowns.has(itemText);
    },
    closeAllDropdowns() {
      this.openDropdowns.clear();
    },
    handleClickOutside(event) {
      // Check if the click is outside all dropdown elements
      if (!event.target.closest('.dropdown') && !event.target.closest('.mobile-dropdown')) {
        this.openDropdowns.clear();
        this.openMobileDropdowns.clear();
      }
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

      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        // Check for pages with single dark full-height sections (like nick-ai, resume)
        const allPageSections = document.querySelectorAll('.page-section');
        const darkSections = document.querySelectorAll('[data-section-theme="dark"]');
        const blackSections = document.querySelectorAll('[data-section-color="black"]');


        // Apply dark theme if there's exactly one PageSection AND it has dark theme
        if (allPageSections.length === 1 && darkSections.length === 1 && blackSections.length === 1) {
          this.headerBackgroundColor = blackSections[0].dataset.sectionColor;
          this.overlayTheme = darkSections[0].dataset.sectionTheme;
          return;
        }

        // Fallback: Try intersection detection with multiple check points
        const headerRect = headerEl.getBoundingClientRect();
        const checkPoints = [
          { x: window.innerWidth / 2, y: headerRect.bottom + 20 },
          { x: window.innerWidth / 2, y: headerRect.bottom + 50 },
          { x: window.innerWidth / 2, y: headerRect.bottom + 100 }
        ];

        // Temporarily disable pointer events
        headerEl.style.pointerEvents = 'none';

        let colorSection = null;
        let themeSection = null;

        for (const point of checkPoints) {
          const elementUnder = document.elementFromPoint(point.x, point.y);
          if (elementUnder && elementUnder.tagName !== 'HTML' && elementUnder.tagName !== 'BODY') {
            colorSection = elementUnder.closest('[data-section-color]');
            themeSection = elementUnder.closest('[data-section-theme]');
            if (colorSection || themeSection) break;
          }
        }

        headerEl.style.pointerEvents = 'auto';

        const terminalInputElement = document.querySelector('[data-has-terminal-input]');
        this.useTerminalInput = terminalInputElement && terminalInputElement.dataset.hasTerminalInput === 'true';

        this.headerBackgroundColor = colorSection
          ? colorSection.dataset.sectionColor
          : (window.scrollY > 0 ? 'white' : 'transparent');
        this.overlayTheme = themeSection ? themeSection.dataset.sectionTheme : 'light';

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
  z-index: var(--z-index-header);
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
  z-index: var(--z-index-modal);
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
  z-index: var(--z-index-drawer);
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
  color: #2a2a2a;
}

/* Hamburger Menu Button - Hidden on desktop */
.site-header__hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  z-index: var(--z-index-drawer);
  font-size: 2rem;
  line-height: 1;
  padding: 0;
}

.site-header__icons {
  gap: .5rem;
}

.ai-icon {
  text-decoration: none;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
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
  box-shadow: 0 10px 15px -3px #0000004d, 0 -4px 6px -2px #0000000d;
  transition: all 0.3s ease-in-out;
}

.theme-dark .pod {
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37),
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
  z-index: var(--z-index-highest);
  /* Semi-transparent background for backdrop-filter to work */
  background-color: rgba(255, 255, 255, 0.8);
  /* Add backdrop-filter for blur effect */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding-top: 80px;
  transform: translateY(-100%);
  transition: transform 0.3s ease;
}

.theme-dark .site-header__mobile-nav {
  /* Semi-transparent dark background */
  background-color: rgba(26, 26, 26, 0.8);
  color: #fff;
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

.site-header__mobile-nav-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.5rem;
  color: inherit;
  z-index: var(--z-index-drawer);
  padding: 0.5rem;
  border-radius: 50%;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.site-header__mobile-nav-close:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.theme-dark .site-header__mobile-nav-close:hover {
  background-color: rgba(255, 255, 255, 0.1);
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

  .site-header--mobile-condensed .terminal-icon,
  .site-header--mobile-condensed .ai-icon {
    display: none !important;
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

/* Dropdown Styles */
.site-header__nav-item.has-dropdown {
  position: relative;
}

.dropdown {
  position: relative;
}

.dropdown-toggle {
  background: none;
  border: none;
  color: inherit;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: inherit;
  padding: 0;
}

.dropdown-arrow {
  font-size: 0.8em;
  transition: transform 0.3s ease;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  list-style: none;
  padding: 0.5rem 0;
  min-width: 180px;
  z-index: var(--z-index-modal);
  margin: 0.5rem 0 0;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.pod .dropdown-menu {
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.theme-dark .dropdown-menu {
  border: 1px solid #404040;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  color: #fff;
}

.theme-light .dropdown-menu {
  color: #000;
}

.dropdown-item {
  margin: 0;
}

.dropdown-item a {
  display: block;
  padding: 0.5rem 1rem;
  color: inherit;
  text-decoration: none;
  transition: background-color 0.2s ease;
}

.dropdown-item a:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.theme-dark .dropdown-item a:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

/* Mobile dropdown styles */
.mobile-dropdown-toggle {
  background: none;
  border: none;
  color: inherit;
  font-size: clamp(1.3rem, 1.3rem + 0.5vw, 1.8rem);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0;
  width: 100%;
  justify-content: center;
}

.mobile-dropdown-menu {
  list-style: none;
  margin: 0.5rem 0 0 0;
  padding: 0;
}

.mobile-dropdown-item {
  margin: 0.5rem 0;
}

.mobile-dropdown-item a {
  display: block;
  color: inherit;
  text-decoration: none;
  font-size: 1.1rem;
  padding: 0.25rem 0;
  transition: color 0.3s ease;
}

.mobile-dropdown-item a:hover {
  color: #666;
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
