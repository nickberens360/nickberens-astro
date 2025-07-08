<template>
  <header class="site-header">
    <div class="site-header__container">
      <div class="site-header__logo">
        <h1>nickberens <span class="git">git: <span class="git-paren">(</span><span class="git-branch">{{ gitBranch }}</span><span class="git-paren">)</span></span><span class="git-emoji"> ✗ </span></h1>
      </div>
      <nav class="site-header__nav">
        <ul class="site-header__nav-list">
          <li class="site-header__nav-item"><a href="/">Home</a></li>
          <li class="site-header__nav-item"><a href="/about">About</a></li>
          <li class="site-header__nav-item"><a href="/projects">Projects</a></li>
          <li class="site-header__nav-item"><a href="/contact">Contact</a></li>
        </ul>
      </nav>
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
  }
}
</script>

<style scoped>
.site-header {
  position: fixed;
  width: 100%;
  padding: 1rem 0;
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

.site-header__nav-item a:hover {
  color: #666;
}
</style>
