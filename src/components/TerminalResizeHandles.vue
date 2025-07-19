<template>
  <template v-if="!isMaximized">
    <div class="resize-handle resize-n" @pointerdown="$emit('startResize', 'n', $event)"></div>
    <div class="resize-handle resize-e" @pointerdown="$emit('startResize', 'e', $event)"></div>
    <div class="resize-handle resize-s" @pointerdown="$emit('startResize', 's', $event)"></div>
    <div class="resize-handle resize-w" @pointerdown="$emit('startResize', 'w', $event)"></div>
    <div class="resize-handle resize-ne" @pointerdown="$emit('startResize', 'ne', $event)"></div>
    <div class="resize-handle resize-se" :class="`theme-${theme}`" @pointerdown="$emit('startResize', 'se', $event)"></div>
    <div class="resize-handle resize-sw" @pointerdown="$emit('startResize', 'sw', $event)"></div>
    <div class="resize-handle resize-nw" @pointerdown="$emit('startResize', 'nw', $event)"></div>
  </template>
</template>

<script>
export default {
  name: 'TerminalResizeHandles',
  props: {
    isMaximized: {
      type: Boolean,
      default: false
    },
    theme: {
      type: String,
      default: 'dark'
    }
  },
  emits: ['startResize']
};
</script>

<style scoped>
/* Resize handle styles */
.resize-handle {
  position: absolute;
  background: transparent;
  touch-action: none;
  z-index: 10;
}

.resize-ne, .resize-se, .resize-sw, .resize-nw {
  width: 15px;
  height: 15px;
}

.resize-n, .resize-s {
  height: 8px;
  left: 8px;
  right: 8px;
}

.resize-e, .resize-w {
  width: 8px;
  top: 8px;
  bottom: 8px;
}

.resize-n { top: 0; cursor: ns-resize; }
.resize-e { right: 0; cursor: ew-resize; }
.resize-s { bottom: 0; cursor: ns-resize; }
.resize-w { left: 0; cursor: ew-resize; }
.resize-ne { top: 0; right: 0; cursor: nesw-resize; }
.resize-se { bottom: 0; right: 0; cursor: nwse-resize; }
.resize-sw { bottom: 0; left: 0; cursor: nesw-resize; }
.resize-nw { top: 0; left: 0; cursor: nwse-resize; }

.resize-se::before {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 9px;
  height: 9px;
  border-right: 2px solid rgba(255, 255, 255, 0.5);
  border-bottom: 2px solid rgba(255, 255, 255, 0.5);
}

.resize-se.theme-light::before {
  border-right: 2px solid rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid rgba(0, 0, 0, 0.3);
}
</style>