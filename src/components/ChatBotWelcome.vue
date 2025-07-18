<template>
  <div
    class="welcome-container"
    :class="`theme-${theme}`"
  >
    <div class="welcome-content">
      <pre class="welcome-content__ascii">███╗   ██╗██╗ ██████╗██╗  ██╗    █████╗ ██╗
████╗  ██║██║██╔════╝██║ ██╔╝   ██╔══██╗██║
██╔██╗ ██║██║██║     █████╔╝    ███████║██║
██║╚██╗██║██║██║     ██╔═██╗    ██╔══██║██║
██║ ╚████║██║╚██████╗██║  ██╗██╗██║  ██║██║
╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝</pre>
      <h2>Welcome to nick.AI</h2>
      <p>Try asking me some questions like:</p>
      <ul class="example-prompts">
        <li @click="selectPrompt('Tell me about Nick')">
          <span class="prompt-icon">→</span>
          Tell me about Nick
        </li>
        <li @click="selectPrompt('Show all illustrations')">
          <span class="prompt-icon">→</span>
          Show all illustrations
        </li>
        <li @click="selectPrompt('Show me images of Doug')">
          <span class="prompt-icon">→</span>
          Show me images of Doug
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatBotWelcome',
  props: {
    theme: {
      type: String,
      default: 'dark',
      validator: (value) => ['light', 'dark'].includes(value)
    }
  },
  emits: ['select-prompt'],
  setup(props, { emit }) {
    const selectPrompt = (prompt) => {
      emit('select-prompt', prompt);
    };

    return {
      selectPrompt
    };
  }
};
</script>

<style scoped>
.welcome-container {
  /*background: radial-gradient(circle, rgba(230, 115, 115, 0.05), rgba(115, 230, 115, 0.05), rgba(115, 115, 230, 0.05));*/
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
  background-color: #f9fafb;
}

.welcome-content {
  max-width: 500px;
  margin: 0 auto;
}

.welcome-content__ascii {
  background: linear-gradient(to right, #ff0000, #00ff00, #0000ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;

}

h2 {
  margin-bottom: 1rem;
  font-size: 1.5rem;
  font-weight: 600;
}

p {
  margin-bottom: 1.5rem;
  font-size: 1rem;
  color: #4b5563;
}

.example-prompts {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.example-prompts li {
  padding: 0.75rem 1.25rem;
  background-color: #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  display: flex;
  align-items: center;
}

.example-prompts li:hover {
  background-color: #d1d5db;
  transform: translateY(-2px);
}

.prompt-icon {
  margin-right: 0.5rem;
  font-weight: bold;
}

/* Dark theme styles */
.theme-dark {
  background-color: #111111;
  color: #f9fafb;
}

.theme-dark p {
  color: #d1d5db;
}

.theme-dark .example-prompts li {
  background-color: #222222;
  color: #f9fafb;
}

.theme-dark .example-prompts li:hover {
  background-color: #333333;
}
@media (max-width: 768px) {
  .welcome-content__ascii {
    font-size: 8px;
  }
}
</style>