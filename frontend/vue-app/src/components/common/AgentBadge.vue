<template>
  <span class="agent-badge" :class="`agent-badge--${agent.toLowerCase()}`">
    <span>{{ icon }}</span>
    <span>{{ agent }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  agent: 'Guide' | 'Tutor' | 'Evaluator';
}>();

const icon = computed(() => ({
  Guide: 'Guide',
  Tutor: 'Tutor',
  Evaluator: 'Eval',
}[props.agent]));
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 12px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  transition: background 0.5s ease, transform 0.3s ease;

  &--guide {
    background: $agent-guide-gradient;
  }

  &--tutor {
    background: $agent-tutor-gradient;
  }

  &--evaluator {
    background: $agent-evaluator-gradient;
  }
}
</style>
