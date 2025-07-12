<template>
  <header
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
            <span class="git">git:
            <span class="git-paren">(</span>
            <span class="git-branch">{{ gitBranch }}</span>
            <span class="git-paren">)</span>
          </span>
          </p>
        </a>
        <TerminalInput />
      </div>

      <nav
        class="site-header__nav"
        :class="[variant === 'pod' ? 'pod' : '']"
        :style="variant === 'pod' ? headerStyles : {}"
        ref="nav"
      >
        <ul class="site-header__nav-list">
          <li class="site-header__nav-item"><a href="/">Home</a></li>
          <li class="site-header__nav-item"><a href="/atomic-docs">Atomic Docs</a></li>
          <li class="site-header__nav-item"><a href="/illustrations">Illustrations</a></li>
          <li class="site-header__nav-item"><a href="/resume">Resume</a></li>
          <li class="site-header__nav-item"><a href="/#contact">Contact</a></li>
          <li v-if="isMounted" class="site-header__nav-item">
            <a href="https://github.com/nickberens360" target="_blank" rel="noopener noreferrer" aria-label="GitHub Profile">
              <font-awesome-icon size="2x" :icon="['fab', 'github']" />
            </a>
          </li>
        </ul>
      </nav>
    </div>
  </header>
</template>

<script>
import { library } from '@fortawesome/fontawesome-svg-core';
import { faGithub } from '@fortawesome/free-brands-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import TerminalInput from './TerminalInput.vue';

library.add(faGithub)

export default {
  name: 'SiteHeader',
  components: {
    TerminalInput,
    FontAwesomeIcon
  },
  props: {
    gitBranch: {
      type: String,
      default: 'main'
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
      isMounted: false,
    };
  },
  computed: {
    headerStyles() {
      if (!this.isMounted) {
        return { backgroundColor: 'transparent' };
      }
      return {
        backgroundColor: this.headerBackgroundColor,
      };
    }
  },
  mounted() {
    this.isMounted = true;
    window.addEventListener('scroll', this.handleScroll, { passive: true });
    this.handleScroll();
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.handleScroll);
  },
  methods: {
    handleScroll() {
      const headerEl = this.$refs.siteHeader;
      if (!headerEl) return;
      const headerRect = headerEl.getBoundingClientRect();
      const checkX = window.innerWidth / 2;
      const checkY = headerRect.top + (headerRect.height / 2) + 34;
      headerEl.style.pointerEvents = 'none';
      const elementUnder = document.elementFromPoint(checkX, checkY);
      headerEl.style.pointerEvents = 'auto';
      if (!elementUnder) {
        this.headerBackgroundColor = window.scrollY > 0 ? 'white' : 'transparent';
        this.overlayTheme = 'light';
        return;
      }
      const colorSection = elementUnder.closest('[data-section-color]');
      const themeSection = elementUnder.closest('[data-section-theme]');
      this.headerBackgroundColor = colorSection
        ? colorSection.dataset.sectionColor
        : (window.scrollY > 0 ? 'white' : 'transparent');
      this.overlayTheme = themeSection ? themeSection.dataset.sectionTheme : 'light';
    }
  }
}
</script>

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
}

.theme-dark .site-header__logo {
  color: #fff;
}

.site-header__logo a {
  color: black;
  text-decoration: none;
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
  transition: color 0.3s ease;
}

.site-header.theme-light .site-header__nav-item a:hover {
  color: #666;
}

.pod {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 85%;
  padding: 0 1.5rem;
  border-radius: 200px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 -4px 6px -2px rgba(0, 0, 0, 0.05);
  transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out, color 0.3s ease-in-out;
}

.theme-dark .pod {
  box-shadow: 0 10px 15px -3px rgba(255, 255, 255, 0.1), 0 4px 6px -4px rgba(255, 255, 255, 0.05);
}

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
</style>