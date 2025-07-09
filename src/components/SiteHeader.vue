<template>
  <header
    class="site-header"
    :class="[`theme-${overlayTheme}`]"
    :style="headerStyles"
    ref="siteHeader"
  >
    <div class="site-header__container">
      <a href="/" class="site-header__logo">
        <p>nickberens <span class="git">git: <span class="git-paren">(</span><span class="git-branch">{{ gitBranch }}</span><span class="git-paren">)</span></span><span class="git-emoji"> ✗ </span></p>
      </a>

      <button class="site-header__hamburger" :class="{ 'is-active': isMobileMenuOpen }" @click="toggleMobileMenu" aria-label="Toggle menu">
        🍔
      </button>

      <nav class="site-header__nav">
        <ul class="site-header__nav-list">
          <li class="site-header__nav-item"><a href="/">Home</a></li>
          <li class="site-header__nav-item"><a href="/resume">Resume</a></li>
          <li class="site-header__nav-item"><a href="/projects">Projects</a></li>
          <li class="site-header__nav-item"><a href="/blog">Blog</a></li>
          <li class="site-header__nav-item"><a href="#contact">Contact</a></li>
          <li v-if="isMounted" class="site-header__nav-item">
            <a href="https://github.com/nickberens360" target="_blank" rel="noopener noreferrer" aria-label="GitHub Profile">
              <font-awesome-icon size="2x" :icon="['fab', 'github']" />
            </a>
          </li>
        </ul>
      </nav>

      <div class="site-header__mobile-nav" :class="{ 'is-active': isMobileMenuOpen }" :style="headerStyles">
        <ul class="site-header__mobile-nav-list">
          <li class="site-header__mobile-nav-item"><a href="/" @click="closeMobileMenu">Home</a></li>
          <li class="site-header__mobile-nav-item"><a href="/resume" @click="closeMobileMenu">Resume</a></li>
          <li class="site-header__mobile-nav-item"><a href="/projects" @click="closeMobileMenu">Projects</a></li>
          <li class="site-header__mobile-nav-item"><a href="#contact" @click="closeMobileMenu">Contact</a></li>
          <li v-if="isMounted" class="site-header__mobile-nav-item">
            <a href="https://github.com/nickberens360" target="_blank" rel="noopener noreferrer" aria-label="GitHub Profile" @click="closeMobileMenu">
              <font-awesome-icon :icon="['fab', 'github']" />
              <span style="margin-left: 0.5em;">GitHub</span>
            </a>
          </li>
        </ul>
      </div>
    </div>
  </header>
</template>

<script>
// --- ADD THESE IMPORTS ---
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { library } from '@fortawesome/fontawesome-svg-core'
import { faGithub } from '@fortawesome/free-brands-svg-icons'

// --- ADD THE ICON TO THE LIBRARY ---
library.add(faGithub)


export default {
  name: 'SiteHeader',
  // --- ADD THIS COMPONENTS OBJECT ---
  components: {
    FontAwesomeIcon
  },
  props: {
    gitBranch: {
      type: String,
      default: 'main'
    }
  },
  data() {
    return {
      overlayTheme: 'light',
      headerBackgroundColor: 'transparent',
      isMobileMenuOpen: false,
      isMounted: false
    };
  },
  computed: {
    headerStyles() {
      if (!this.isMounted) {
        return { backgroundColor: 'transparent' };
      }
      const styles = {
        backgroundColor: this.headerBackgroundColor,
      };
      return styles;
    }
  },
  mounted() {
    this.isMounted = true;
    window.addEventListener('scroll', this.handleScroll, { passive: true });
    this.handleScroll();
  },
  beforeDestroy() {
    window.removeEventListener('scroll', this.handleScroll);
  },
  methods: {
    toggleMobileMenu() {
      this.isMobileMenuOpen = !this.isMobileMenuOpen;
      document.body.style.overflow = this.isMobileMenuOpen ? 'hidden' : '';
    },
    closeMobileMenu() {
      this.isMobileMenuOpen = false;
      document.body.style.overflow = '';
    },
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
  width: 100%;
  padding: 1rem 0;
  z-index: 100;
  transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out, color 0.3s ease-in-out;
}

/* --- Theme-based Styling for Text --- */

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

.site-header__container {
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
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


.site-header__logo p {
  margin: 0;
  font-size: clamp(1.2rem, 1.2rem + 0.5vw, 1.5rem);
  font-weight: bold;
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

.site-header__nav-item a {
  text-decoration: none;
  color: inherit;
  transition: color 0.3s ease;
}

.site-header.theme-light .site-header__nav-item a:hover {
  color: #666;
}

/* Hamburger Menu Button */
.site-header__hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  z-index: 1001;
  font-size: 2rem;
  line-height: 1;
}

.site-header__hamburger span {
  display: block;
  width: 25px;
  height: 3px;
  margin: 5px 0;
  background-color: #000;
  transition: all 0.3s ease;
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

/* Responsive Styles */
@media (max-width: 768px) {
  .site-header__nav {
    display: none;
  }

  .site-header__hamburger {
    display: block;
  }

  .site-header__mobile-nav {
    display: block;
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
}
</style>
