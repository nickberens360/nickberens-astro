<template>
  <footer class="site-footer theme-dark" :class="[`theme-${theme}`]">
    <div class="site-footer__container">
      <div class="site-footer__content">
        <p class="copyright">
          <span style="color: rgba(255,255,0,0.74)">© 2025 Nick Berens</span>
        </p>
        <p class="site-footer__text">
          <span class="git">git: <span class="git-paren">(</span><span class="git-hash">
            <a :href="`${repoUrl}/commit/${commitHash}`" target="_blank" rel="noopener noreferrer">
              {{ commitHash }}
            </a>
          </span><span class="git-paren">)</span></span>
        </p>
      </div>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'SiteFooter',
  props: {
    commitHash: {
      type: String,
      default: 'unknown'
    },
    repoUrl: {
      type: String,
      default: 'https://github.com'
    },
    theme: {
      type: String,
      default: 'light'
    }
  }
}
</script>

<style scoped>
.site-footer {
  padding: 1rem 0;
  width: 100%;
  transition: background-color 0.3s ease-in-out, color 0.3s ease-in-out;
  border-top: 1px dashed #222222;
}

.site-footer__container {
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

.site-footer__content {
  text-align: center;
  display: flex;
  align-items: center;
}

.site-footer__text {
  margin: 0;
  font-size: 0.9rem;
}

/* Theme-based Styling */
.site-footer.theme-light {
  color: white;
  background-color: black;
}

.site-footer.theme-light .git {
  color: blue;
}

.site-footer.theme-light .git-hash a {
  color: red;
  text-decoration: none;
}

.site-footer.theme-light .git-hash a:hover {
  text-decoration: underline;
}

/*.site-footer.theme-dark {
  color: #ffffff;
  background-color: #333333;
}*/

.site-footer.theme-dark .git {
  color: #82aaff;
}

.site-footer.theme-dark .git-paren {
  color: #82aaff;
}

.site-footer.theme-dark .git-hash a {
  color: #ff8282;
  text-decoration: none;
}

.site-footer.theme-dark .git-hash a:hover {
  text-decoration: underline;
}

.copyright {
  display: block;
  font-size: 0.9rem;
  margin-right: 2rem;
}

@media (max-width: 768px) {
  .site-footer__text, .copyright {
    font-size: 0.8rem;
  }
}
</style>
