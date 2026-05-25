<template>
  <div v-if="visible" class="websocket-toast" :class="`websocket-toast--${type}`">
    <strong>{{ title }}</strong>
    <p>{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  visible: boolean;
  title: string;
  message: string;
  type?: 'trigger' | 'help' | 'switch';
}>(), {
  type: 'trigger',
});
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.websocket-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  min-width: 300px;
  padding: 16px 20px;
  border-left: 4px solid $accent-orange;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  animation: slideInFromRight 0.3s ease;

  p {
    margin-top: 4px;
    color: $text-secondary;
  }

  &--help {
    border-left-color: $accent-red;
  }

  &--switch {
    border-left-color: $accent-green;
  }
}
</style>
