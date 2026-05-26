<template>
  <button class="gradient-button" :type="nativeType" :disabled="disabled">
    <slot />
  </button>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  nativeType?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
}>(), {
  nativeType: 'button',
  disabled: false,
});
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.gradient-button {
  border: none;
  border-radius: $radius-button;
  padding: 14px 40px;
  color: white;
  font-size: 18px;
  font-weight: 700;
  background: $btn-gradient;
  box-shadow: $shadow-btn;
  cursor: pointer;
  transition: $transition-default;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: $shadow-btn-hover;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
}
</style>
