<template>
  <div class="terminal-easter-egg-wrapper">
    <div class="terminal-celebration">
     <pre class="ascii-art">
 /$$     /$$ /$$$$$$$$  /$$$$$$  /$$
|  $$   /$$/| $$_____/ /$$__  $$| $$
 \  $$ /$$/ | $$      | $$  \__/| $$
  \  $$$$/  | $$$$$   |  $$$$$$ | $$
   \  $$/   | $$__/    \____  $$|__/
| $$    | $$       /$$ \  $$
    | $$    | $$$$$$$$|  $$$$$$/ /$$
    |__/    |________/ \______/ |__/
      </pre>

      <div class="message-container text-center">
        <div class="typewriter">
          <span class="prompt">~$</span> <span class="success-text">{{ eggMessage }}</span>
        </div>
        <div class="achievement-badge">
          <span class="badge-icon">🏆</span>
          <span class="badge-text">Achievement Unlocked!</span>
        </div>
      </div>
      <div class="matrix-rain">
        <span v-for="n in 30" :key="n" class="matrix-drop">{{ getRandomChar() }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, onMounted } from 'vue';

const MATRIX_CHARS = 'ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ01';

export default {
  name: 'TerminalEasterEgg',
  props: {
    eggName: {
      type: String,
      required: true
    },
    theme: {
      type: String,
      default: 'dark'
    }
  },
  setup(props) {
    const eggMessage = computed(() => {
      const messages = {
        egg1: 'Screen cleaning protocol activated! 🧹',
        egg2: 'Egg discussion initiated successfully! 🥚',
        egg3: 'Terminal velocity: 53 m/s! 🚀'
      };
      return messages[props.eggName] || 'Secret discovered!';
    });

    const getRandomChar = () => {
      return MATRIX_CHARS[Math.floor(Math.random() * MATRIX_CHARS.length)];
    };

    return {
      eggMessage,
      getRandomChar
    };
  }
};
</script>

<style scoped>
.terminal-easter-egg-wrapper {
  margin: 8px 0;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
}

.terminal-celebration {
  position: relative;
  background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
  border: 1px solid #00ff00;
  border-radius: 4px;
  padding: 20px;
  overflow: hidden;
}

.ascii-art {
  color: #00ff00;
  text-align: center;
  font-size: 10px;
  line-height: 1.2;
  margin: 0 0 15px 0;
  text-shadow: 0 0 5px #00ff00;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.8;
  }
  50% {
    opacity: 1;
  }
}

.message-container {
  position: relative;
  z-index: 2;
}

.typewriter {
  margin-bottom: 10px;
  overflow: hidden;
  white-space: nowrap;
}

.prompt {
  color: #00ff00;
  font-weight: bold;
}

.success-text {
  color: #00ff00;
  text-shadow: 0 0 3px #00ff00;
}

.achievement-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 255, 0, 0.1);
  border: 1px solid rgba(0, 255, 0, 0.3);
  border-radius: 20px;
  padding: 6px 16px;
  margin-top: 10px;
  animation: slideIn 0.6s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.badge-icon {
  font-size: 18px;
  animation: rotate 2s ease-in-out infinite;
}

@keyframes rotate {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-10deg);
  }
  75% {
    transform: rotate(10deg);
  }
}

.badge-text {
  color: #00ff00;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Matrix rain effect */
.matrix-rain {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  opacity: 0.1;
  pointer-events: none;
}

.matrix-drop {
  position: absolute;
  color: #00ff00;
  font-size: 14px;
  animation: matrix-fall linear infinite;
  text-shadow: 0 0 5px #00ff00;
}

.matrix-drop:nth-child(odd) {
  left: 5%;
  animation-duration: 3s;
  animation-delay: 0s;
}

.matrix-drop:nth-child(even) {
  left: 15%;
  animation-duration: 4s;
  animation-delay: 0.5s;
}

.matrix-drop:nth-child(3n) {
  left: 25%;
  animation-duration: 3.5s;
  animation-delay: 1s;
}

.matrix-drop:nth-child(4n) {
  left: 35%;
  animation-duration: 4.5s;
  animation-delay: 1.5s;
}

.matrix-drop:nth-child(5n) {
  left: 45%;
  animation-duration: 3s;
  animation-delay: 2s;
}

.matrix-drop:nth-child(6n) {
  left: 55%;
  animation-duration: 3.8s;
  animation-delay: 0.3s;
}

.matrix-drop:nth-child(7n) {
  left: 65%;
  animation-duration: 4.2s;
  animation-delay: 0.8s;
}

.matrix-drop:nth-child(8n) {
  left: 75%;
  animation-duration: 3.3s;
  animation-delay: 1.3s;
}

.matrix-drop:nth-child(9n) {
  left: 85%;
  animation-duration: 4s;
  animation-delay: 1.8s;
}

.matrix-drop:nth-child(10n) {
  left: 95%;
  animation-duration: 3.6s;
  animation-delay: 2.3s;
}

@keyframes matrix-fall {
  0% {
    top: -10%;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    top: 110%;
    opacity: 0;
  }
}

/* Light theme adjustments */
.theme-light .terminal-celebration {
  background: linear-gradient(135deg, #f0f0f0 0%, #e0e0e0 50%, #d0d0d0 100%);
  border-color: #0066cc;
}

.theme-light .ascii-art,
.theme-light .prompt,
.theme-light .success-text,
.theme-light .badge-text {
  color: #0066cc;
  text-shadow: 0 0 3px rgba(0, 102, 204, 0.5);
}

.theme-light .achievement-badge {
  background: rgba(0, 102, 204, 0.1);
  border-color: rgba(0, 102, 204, 0.3);
}

.theme-light .matrix-drop {
  color: #0066cc;
  text-shadow: 0 0 5px rgba(0, 102, 204, 0.5);
}

.theme-light .terminal-celebration {
  animation: glow-light 2s ease-in-out infinite alternate;
}

@keyframes glow-light {
  from {
    box-shadow: 0 0 5px #0066cc, 0 0 10px #0066cc;
  }
  to {
    box-shadow: 0 0 10px #0066cc, 0 0 20px #0066cc, 0 0 30px #0066cc;
  }
}
</style>