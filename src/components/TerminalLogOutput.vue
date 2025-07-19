<template>
  <div
    class="terminal-log-output"
    :class="`theme-${theme}`"
  >
    <!-- Individual commit line display -->
    <template v-if="commit">
      <div class="commit-line">
        <span class="commit-hash">[{{ commit.hash }}]</span>
        <a v-if="commit.url" :href="commit.url" class="terminal-link">View on GitHub</a>
        <span class="commit-message">{{ commit.message }}</span>
      </div>
    </template>

    <!-- Full commit history display -->
    <div v-if="commitHistory && commitHistory.isVisible" class="commit-history-container">
      <div class="commit-history-title">{{ commitHistory.title }}</div>

      <div v-if="commitHistory.error" class="commit-history-error">
        <div class="commit-history-error-icon">⚠️</div>
        <div class="commit-history-error-message">{{ commitHistory.message }}</div>
      </div>

      <template v-else>
        <div v-for="(commit, index) in commitHistory.commits" :key="index" class="commit-item">
          <span class="commit-hash">[{{ commit.hash }}]</span>
          <a v-if="commit.url" :href="commit.url" class="terminal-link">View on GitHub</a>
          <span class="commit-message">{{ commit.message }}</span>
        </div>
      </template>

      <div v-if="!commitHistory.error && commitHistory.note" class="commit-history-note">
        {{ commitHistory.note }}
      </div>
    </div>
  </div>
</template>

<script>
// Export the function separately
export function processCommitHistory(commits) {
  if (commits && commits.error) {
    return {
      title: 'Git Commit History',
      commits: [],
      message: commits.message,
      isVisible: true,
      error: true
    };
  }

  if (!Array.isArray(commits)) {
    return {
      title: 'Git Commit History',
      commits: [],
      message: 'Invalid data format received',
      isVisible: true,
      error: true
    };
  }

  if (commits.length === 0) {
    return {
      title: 'Git Commit History',
      commits: [],
      message: 'No commit history available.',
      isVisible: true,
      error: true
    };
  }

  return {
    title: 'Git Commit History',
    commits: commits.map(commit => ({
      hash: commit.hash,
      message: commit.message,
      url: commit.url
    })),
    note: `Showing ${commits.length} most recent commits`,
    isVisible: true,
    error: false
  };
}

export default {
  name: 'TerminalLogOutput',
  props: {
    commit: {
      type: Object,
      default: null
    },
    commitHistory: {
      type: Object,
      default: null
    },
    theme: {
      type: String,
      default: 'dark'
    }
  },
  methods: {
    processCommitHistory
  }
};
</script>

<style scoped>
/* Commit history container styling */
.commit-history-container {
  margin-top: 10px;
  margin-bottom: 10px;
  padding: 5px;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.2);
}

.commit-history-title {
  color: #ffffff;
  font-weight: bold;
  font-size: 1.1em;
  text-decoration: underline;
  margin-bottom: 10px;
}

.commit-item {
  margin: 5px 0;
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
}

.commit-line {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  margin: 2px 0;
}

.commit-hash {
  color: #ffbd2e;
  font-weight: bold;
  margin-right: 10px;
  font-family: monospace;
}

.commit-message {
  margin-left: 5px;
  white-space: pre-wrap;
  word-break: break-word;
}

.terminal-link {
  color: #3498db;
  text-decoration: underline;
  cursor: pointer;
  margin-right: 10px;
}

.terminal-link:hover {
  color: #2980b9;
}

.commit-history-note {
  color: #aaaaaa;
  font-style: italic;
  font-size: 0.85em;
  margin-top: 8px;
}

/* Error display styling */
.commit-history-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 15px 10px;
  text-align: center;
}

.commit-history-error-icon {
  font-size: 20px;
  margin-bottom: 8px;
}

.commit-history-error-message {
  font-size: 14px;
  color: #cccccc;
  font-style: italic;
}

/* Theme-specific styling */
.theme-light .commit-history-container {
  border-color: #ccc;
  background-color: rgba(0, 0, 0, 0.05);
}

.theme-light .commit-history-title {
  color: #333333;
}

.theme-light .commit-hash {
  color: orange;
}

.theme-light .terminal-link {
  color: blue;
}

.theme-light .terminal-link:hover {
  color: blueviolet;
}

.theme-light .commit-history-note {
  color: #777777;
}

.theme-light .commit-history-error-message {
  color: #666666;
}
.theme-light .commit-message {
  color: #333;
}

</style>
