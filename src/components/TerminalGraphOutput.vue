<template>
  <div
    class="terminal-output"
    :class="`theme-${theme}`"
  >
    <!-- Graph history output -->
    <template v-if="line && line.type === 'graph-history'">
      <span class="git-graph-date">{{ line.date }}:</span>
      <span class="git-graph-additions">{{ line.additionBars }}</span>
      <span class="git-graph-deletions">{{ line.deletionBars }}</span>
      <span class="git-graph-stats">({{ line.additions }} additions, {{ line.deletions }} deletions)</span>
    </template>

    <!-- Latest commit output -->
    <template v-else-if="line && line.type === 'latest-commit'">
      <div class="git-latest-commit-container">
        <div class="git-graph-title">{{ line.title }}</div>
        <div class="latest-commit-content">
          <div class="latest-commit-line">
            <span class="latest-commit-hash">[{{ line.hash }}]</span>
            <a v-if="line.url" :href="line.url" class="terminal-link">View on GitHub</a>
          </div>
          <div class="latest-commit-message">{{ line.message }}</div>
        </div>
      </div>
    </template>

    <!-- Graph data visualization -->
    <div v-if="graphData && graphData.isVisible" class="git-graph-container">
      <div class="git-graph-title">{{ graphData.title }}</div>

      <div v-if="graphData.noData" class="git-graph-no-data">
        <div class="git-graph-no-data-icon">📊</div>
        <div class="git-graph-no-data-message">No code frequency data available</div>
        <div class="git-graph-no-data-explanation">{{ graphData.note }}</div>
      </div>

      <template v-else>
        <div v-for="(week, weekIndex) in graphData.weeks" :key="weekIndex" class="git-graph-row">
          <span class="git-graph-date">{{ week.date }}:</span>
          <span class="git-graph-additions">{{ '+'.repeat(week.additionBars) }}</span>
          <span class="git-graph-deletions">{{ '-'.repeat(week.deletionBars) }}</span>
          <span class="git-graph-stats">({{ week.additions }} additions, {{ week.deletions }} deletions)</span>
        </div>
      </template>

      <div v-if="!graphData.noData" class="git-graph-note">{{ graphData.note }}</div>
    </div>

    <!-- Commit data display -->
    <div v-if="commitData && commitData.isVisible" class="git-latest-commit-container">
      <div class="git-graph-title">{{ commitData.title }}</div>
      <div class="latest-commit-content">
        <div class="latest-commit-line">
          <span class="latest-commit-hash">[{{ commitData.hash }}]</span>
          <a v-if="commitData.url" :href="commitData.url" class="terminal-link">View on GitHub</a>
        </div>
        <div class="latest-commit-message">{{ commitData.message }}</div>
      </div>
    </div>
  </div>
</template>

<script>
// Export the processCodeFrequencyData function so it can be imported elsewhere
export function processCodeFrequencyData(frequencyData) {
  if (frequencyData && frequencyData.computing) {
    return { title: 'Code Frequency Data', weeks: [], note: frequencyData.message, isVisible: true, noData: true };
  }
  if (frequencyData && frequencyData.error) {
    return { title: 'Code Frequency Data', weeks: [], note: frequencyData.message, isVisible: true, noData: true };
  }
  if (!Array.isArray(frequencyData)) {
    return { title: 'Code Frequency Data', weeks: [], note: 'Invalid data format received', isVisible: true, noData: true };
  }
  if (frequencyData.length === 0) {
    return { title: 'Code Frequency Data', weeks: [], note: 'No code frequency data available. This could be because the repository is new, private, or the GitHub API has not calculated the statistics yet.', isVisible: true, noData: true };
  }

  const recentData = frequencyData.slice(-10);
  let maxAddition = 0;
  let maxDeletion = 0;
  recentData.forEach(week => {
    maxAddition = Math.max(maxAddition, week[1]);
    maxDeletion = Math.max(maxDeletion, Math.abs(week[2]));
  });
  const maxValue = Math.max(maxAddition, maxDeletion);
  const graphHeight = 10;

  // Avoid division by zero
  const scaleFactor = maxValue > 0 ? graphHeight / maxValue : 0;

  return {
    title: 'Additions (+) / Deletions (-) - Last 10 weeks',
    weeks: recentData.map(week => {
      const date = new Date(week[0] * 1000).toISOString().split('T')[0];
      const additions = week[1];
      const deletions = Math.abs(week[2]);
      const additionBars = maxValue > 0 ? Math.round(additions * scaleFactor) : 0;
      const deletionBars = maxValue > 0 ? Math.round(deletions * scaleFactor) : 0;
      return { date, additions, deletions, additionBars, deletionBars };
    }),
    note: 'Note: Graph is scaled to fit the terminal window',
    isVisible: true,
    noData: false
  };
}

export default {
  name: 'TerminalGraphOutput',
  props: {
    line: {
      type: Object,
      default: null
    },
    graphData: {
      type: Object,
      default: null
    },
    commitData: {
      type: Object,
      default: null
    },
    theme: {
      type: String,
      default: 'dark'
    }
  },
  methods: {
    processCodeFrequencyData
  }
};
</script>

<style scoped>
/* Git graph styling */
.git-graph-additions {
  color: #27c93f; /* Green color for additions */
  font-weight: bold;
  letter-spacing: 1px;
}

.git-graph-deletions {
  color: #ff5f56; /* Red color for deletions */
  font-weight: bold;
  letter-spacing: 1px;
}

.git-graph-date {
  color: #ffbd2e; /* Yellow color for dates */
  font-weight: bold;
}

.git-graph-stats {
  color: #cccccc; /* Light gray for stats */
  font-style: italic;
  font-size: 0.9em;
}

.git-graph-title {
  color: #ffffff; /* White color for title */
  font-weight: bold;
  font-size: 1.1em;
  text-decoration: underline;
  margin-bottom: 10px;
}

.git-graph-note {
  color: #aaaaaa; /* Light gray for note */
  font-style: italic;
  font-size: 0.85em;
}

/* Theme-specific git graph styling */
.theme-light .git-graph-additions {
  color: #27a83f;
}

.theme-light .git-graph-deletions {
  color: #e74c3c;
}

.theme-light .git-graph-date {
  color: #f39c12;
}

.theme-light .git-graph-stats {
  color: #666666;
}

.theme-light .git-graph-title {
  color: #333333;
}

.theme-light .git-graph-note {
  color: #777777;
}

/* Git graph container styling */
.git-graph-container {
  margin-top: 10px;
  margin-bottom: 10px;
  padding: 5px;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.2);
}

.git-graph-row {
  display: flex;
  align-items: center;
  margin: 2px 0;
  white-space: nowrap;
}

/* No data message styling */
.git-graph-no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 10px;
  text-align: center;
}

.git-graph-no-data-icon {
  font-size: 24px;
  margin-bottom: 10px;
}

.git-graph-no-data-message {
  font-size: 14px;
  color: #cccccc;
  font-style: italic;
  margin-bottom: 8px;
}

.git-graph-no-data-explanation {
  font-size: 12px;
  color: #aaaaaa;
  font-style: italic;
  max-width: 80%;
  text-align: center;
  margin-top: 8px;
}

.theme-light .git-graph-container {
  border-color: #ccc;
  background-color: rgba(0, 0, 0, 0.05);
}

.theme-light .git-graph-no-data-message {
  color: #666666;
}

.theme-light .git-graph-no-data-explanation {
  color: #888888;
}

/* Git latest commit container styling - similar to git graph container */
.git-latest-commit-container {
  margin-top: 10px;
  margin-bottom: 10px;
  padding: 5px;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.2);
}

.theme-light .git-latest-commit-container {
  border-color: #ccc;
  background-color: rgba(0, 0, 0, 0.05);
}

.latest-commit-line {
  margin: 5px 0;
}

.latest-commit-hash {
  color: #ffbd2e; /* Yellow color for hash, same as dates in graph */
  font-weight: bold;
  margin-right: 10px;
}

.latest-commit-message {
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Terminal link styling */
.terminal-link {
  color: #3498db;
  text-decoration: underline;
  cursor: pointer;
}

.terminal-link:hover {
  color: #2980b9;
}

.theme-light .terminal-link {
  color: #2980b9;
}

.theme-light .terminal-link:hover {
  color: #1c6ea4;
}
</style>
