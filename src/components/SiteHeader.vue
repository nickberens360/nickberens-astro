<template>
  <header
    class="site-header"
    :class="[`theme-${overlayTheme}`]"
    :style="variant !== 'pod' ? headerStyles : {}"
    ref="siteHeader"
  >
    <div class="site-header__container">
      <a
        href="/"
        class="site-header__logo"
        :class="variant === 'pod' ? 'pod' : ''"
        :style="variant === 'pod' ? headerStyles : {}"
        ref="logo"
      >
        <p>nickberens <span class="git">git: <span class="git-paren">(</span><span class="git-branch">{{ gitBranch }}</span><span class="git-paren">)</span></span><span class="git-emoji"> ✗ </span></p>
      </a>

      <button
        class="site-header__hamburger"
        :class="[{ 'is-active': isMobileMenuOpen }, variant === 'pod' ? 'pod' : '']"
        @click="toggleMobileMenu"
        aria-label="Toggle menu"
        v-show="useMobileLayout"
        :style="variant === 'pod' ? headerStyles : {}"
      >
        🍔
      </button>

      <nav
        class="site-header__nav"
        :class="[variant === 'pod' ? 'pod' : '', {'hidden': useMobileLayout}]"
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

      <div class="site-header__mobile-nav" :class="{ 'is-active': isMobileMenuOpen }" :style="headerStyles">
        <ul class="site-header__mobile-nav-list">
          <li class="site-header__mobile-nav-item"><a href="/" @click="closeMobileMenu">Home</a></li>
          <li class="site-header__mobile-nav-item"><a href="/atomic-docs" @click="closeMobileMenu">Atomic Docs</a></li>
          <li class="site-header__mobile-nav-item"><a href="/illustrations" @click="closeMobileMenu">Illustrations</a></li>
          <li class="site-header__mobile-nav-item"><a href="/resume" @click="closeMobileMenu">Resume</a></li>
          <li class="site-header__mobile-nav-item"><a href="/#contact" @click="closeMobileMenu">Contact</a></li>
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
import { library } from '@fortawesome/fontawesome-svg-core';
import { faGithub } from '@fortawesome/free-brands-svg-icons';
// --- ADD THESE IMPORTS ---
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';

// --- ADD THE ICON TO THE LIBRARY ---
library.add(faGithub)


export default {
  name: 'SiteHeader',
  components: {
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
      isMobileMenuOpen: false,
      isMounted: false,
      useMobileLayout: false
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
    console.log('SiteHeader mounted');
    this.isMounted = true;

    // Create debounced versions of methods
    this.debouncedCheckLayout = this.debounce(this.checkLayoutNeeds, 100);

    // Use debounced version for resize events
    window.addEventListener('scroll', this.handleScroll, { passive: true });
    window.addEventListener('resize', this.debouncedCheckLayout, { passive: true });
    this.handleScroll();

    // Initial layout check might need to be delayed to ensure refs are available
    this.$nextTick(() => {
      console.log('Next tick - checking layout');
      this.checkLayoutNeeds();

      // Force another check after a short delay to ensure everything is rendered
      setTimeout(() => {
        console.log('Forced layout check after timeout');
        this.checkLayoutNeeds();
      }, 100);
    });

    // For more precise tracking, use ResizeObserver
    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        console.log('ResizeObserver triggered');
        this.debouncedCheckLayout();
      });
      this.resizeObserver.observe(this.$refs.siteHeader);
    }
  },
  beforeDestroy() {
    window.removeEventListener('scroll', this.handleScroll);
    window.removeEventListener('resize', this.debouncedCheckLayout);

    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  },
  methods: {
    debounce(func, wait) {
      let timeout;
      return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    },
    checkLayoutNeeds() {
      if (!this.$refs.logo || !this.$refs.nav) {
        console.log('Refs not available yet');
        return;
      }

      const logoRect = this.$refs.logo.getBoundingClientRect();
      const headerWidth = this.$refs.siteHeader.clientWidth;
      const logoRightEdge = logoRect.right;

      // Use percentage-based buffer instead of fixed 20px
      const bufferPercentage = 0.05; // 5% of header width
      const buffer = headerWidth * bufferPercentage;

      // Consider device pixel ratio for high-DPI displays
      const pixelRatio = window.devicePixelRatio || 1;
      const scaledBuffer = buffer * pixelRatio;

      // Improved measurement of hidden nav element
      const navElement = this.$refs.nav;
      const wasHidden = navElement.classList.contains('hidden');
      let navWidth;

      // Create a clone for measurement instead of manipulating the original
      if (wasHidden) {
        const navClone = navElement.cloneNode(true);
        navClone.style.position = 'absolute';
        navClone.style.visibility = 'hidden';
        navClone.style.display = 'block';
        navClone.classList.remove('hidden');
        document.body.appendChild(navClone);

        navWidth = navClone.getBoundingClientRect().width;
        document.body.removeChild(navClone);
      } else {
        navWidth = navElement.getBoundingClientRect().width;
      }

      // Calculate margins between nav items
      const navItems = navElement.querySelectorAll('.site-header__nav-item');
      let totalNavItemsMargin = 0;

      if (navItems.length > 1) {
        // Get the actual margins from computed styles
        const firstItemStyle = window.getComputedStyle(navItems[0]);
        const marginLeft = parseFloat(firstItemStyle.marginLeft);
        // Account for margins between items
        totalNavItemsMargin = marginLeft * (navItems.length - 1);
      }

      // Add margins to the effective nav width
      const effectiveNavWidth = navWidth + totalNavItemsMargin;

      // Calculate available space with percentage-based buffer
      const availableSpace = headerWidth - logoRightEdge - scaledBuffer;

      // Add a breakpoint safety mechanism
      const minDesktopWidth = 768; // Common tablet breakpoint
      const shouldUseMobileLayout =
        (effectiveNavWidth > availableSpace) || (window.innerWidth < minDesktopWidth);

      console.log('Layout check:', {
        headerWidth,
        logoRightEdge,
        buffer: scaledBuffer,
        availableSpace,
        navWidth: effectiveNavWidth,
        shouldUseMobileLayout,
        wasHidden,
        devicePixelRatio: pixelRatio
      });

      this.useMobileLayout = shouldUseMobileLayout;
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

.pod {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 85%;
  padding: 0 1.5rem;
  border-radius: 200px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 -4px 6px -2px rgba(0, 0, 0, 0.05);
  transition: background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out, color 0.3s ease-in-out;

}

.theme-dark .pod {
  box-shadow: 0 10px 15px -3px rgba(255, 255, 255, 0.1), 0 4px 6px -4px rgba(255, 255, 255, 0.05);
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
  font-size: clamp(1rem, 1rem + 0.5vw, 1.5rem);
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

/* Hamburger Menu Button */
.site-header__hamburger {
  background: none;
  border: none;
  cursor: pointer;
  z-index: 1001;
  font-size: 2rem;
  line-height: 1;
  padding: 10px;
  margin-right: -10px; /* Offset the padding */
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

/* Hidden class for dynamic layout switching */
.hidden {
  display: none;
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



/* Dynamic Layout Styles */
/* Hamburger is controlled by v-show="useMobileLayout" */
/* Mobile nav is always in the DOM but transformed off-screen by default */
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
</style>
