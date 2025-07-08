<template>
  <!--
    The background color and box shadow are now applied via a single computed style object.
    This is safer for SSR hydration.
  -->
  <header
    class="site-header"
    :class="[`theme-${overlayTheme}`]"
    :style="headerStyles"
    ref="siteHeader"
  >
    <div class="site-header__container">
      <div class="site-header__logo">
        <h1>nickberens <span class="git">git: <span class="git-paren">(</span><span class="git-branch">{{ gitBranch }}</span><span class="git-paren">)</span></span><span class="git-emoji"> ✗ </span></h1>
      </div>

      <!-- Hamburger menu button for mobile -->
      <button class="site-header__hamburger" :class="{ 'is-active': isMobileMenuOpen }" @click="toggleMobileMenu" aria-label="Toggle menu">
        🍔
      </button>

      <!-- Desktop navigation -->
      <nav class="site-header__nav">
        <ul class="site-header__nav-list">
          <li class="site-header__nav-item"><a href="/">Home</a></li>
          <li class="site-header__nav-item"><a href="/about">About</a></li>
          <li class="site-header__nav-item"><a href="/projects">Projects</a></li>
          <li class="site-header__nav-item"><a href="/contact">Contact</a></li>
        </ul>
      </nav>

      <!-- Mobile navigation -->
      <div class="site-header__mobile-nav" :class="{ 'is-active': isMobileMenuOpen }" :style="headerStyles">
        <ul class="site-header__mobile-nav-list">
          <li class="site-header__mobile-nav-item"><a href="/" @click="closeMobileMenu">Home</a></li>
          <li class="site-header__mobile-nav-item"><a href="/about" @click="closeMobileMenu">About</a></li>
          <li class="site-header__mobile-nav-item"><a href="/projects" @click="closeMobileMenu">Projects</a></li>
          <li class="site-header__mobile-nav-item"><a href="/contact" @click="closeMobileMenu">Contact</a></li>
        </ul>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'SiteHeader',
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
      // This flag prevents client-side logic from running before hydration is complete.
      isMobileMenuOpen: false,
      isMounted: false
    };
  },
  computed: {
    // A computed property to generate the dynamic styles.
    // This avoids using v-bind in CSS which can cause hydration issues.
    headerStyles() {
      // Return a default, server-matching state until the component is mounted on the client.
      if (!this.isMounted) {
        return { backgroundColor: 'transparent' };
      }

      const styles = {
        backgroundColor: this.headerBackgroundColor,
      };

      // if (this.headerBackgroundColor !== 'transparent' && this.overlayTheme === 'light') {
      //   styles.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
      // }

      return styles;
    }
  },
  mounted() {
    // Now that we are on the client and the component is mounted, we can run our logic.
    this.isMounted = true;

    window.addEventListener('scroll', this.handleScroll, { passive: true });

    // We still call handleScroll initially to set the correct state
    // based on the initial page load position (e.g., if loaded from a hash link).
    this.handleScroll();
  },
  beforeDestroy() {
    window.removeEventListener('scroll', this.handleScroll);
  },
  methods: {
    toggleMobileMenu() {
      console.log('Toggle mobile menu clicked', this.isMobileMenuOpen);
      this.isMobileMenuOpen = !this.isMobileMenuOpen;
      console.log('After toggle:', this.isMobileMenuOpen);
      // Prevent scrolling when menu is open
      document.body.style.overflow = this.isMobileMenuOpen ? 'hidden' : '';
    },
    closeMobileMenu() {
      this.isMobileMenuOpen = false;
      document.body.style.overflow = '';
    },
    handleScroll() {
      // This method only runs on the client, so we don't need to worry about the server state.
      const headerEl = this.$refs.siteHeader;
      if (!headerEl) return;

      const headerRect = headerEl.getBoundingClientRect();
      const checkX = window.innerWidth / 2;
      const checkY = headerRect.top + (headerRect.height / 2);

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

      if (window.scrollY > 0) {
        this.headerBackgroundColor = colorSection ? colorSection.dataset.sectionColor : 'white';
      } else {
        this.headerBackgroundColor = 'transparent';
      }

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

.site-header__logo h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: bold;
}

.site-header__nav-list {
  display: flex;
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
  font-size: 1.5rem;
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
