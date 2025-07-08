<template>
  <header class="site-header">
    <div class="site-header__container">
      <div class="site-header__logo">
        <h1>nickberens <span class="git">git: <span class="git-paren">(</span><span class="git-branch">{{ gitBranch }}</span><span class="git-paren">)</span></span><span class="git-emoji"> ✗ </span></h1>
      </div>

      <!-- Hamburger menu button for mobile -->
      <button class="site-header__hamburger" :class="{ 'is-active': isMobileMenuOpen }" @click="toggleMobileMenu" aria-label="Toggle menu">
        <span></span>
        <span></span>
        <span></span>
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
      <div class="site-header__mobile-nav" :class="{ 'is-active': isMobileMenuOpen }">
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
      isMobileMenuOpen: false
    }
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
    }
  }
}
</script>

<style scoped>
.site-header {
  position: fixed;
  width: 100%;
  padding: 1rem 0;
  z-index: 1000;
}

.git {
  color: blue;
}
.git-paren {
  color: blue;
}
.git-branch {
  color: red;
}

.git-emoji {
  color: yellow;
}

.site-header__container {
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.site-header__logo h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: bold;
}

/* Desktop Navigation */
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

.site-header__nav-item a:hover {
  color: #666;
}

/* Hamburger Menu Button */
.site-header__hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 10px;
  z-index: 1001;
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
