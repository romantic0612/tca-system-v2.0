<template>
  <span class="group-badge" :class="`group-badge--${normalized}`">{{ group }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  group: 'SA' | 'EXP' | 'AI-AUTO' | 'TCA';
}>();

const normalized = computed(() => props.group.toLowerCase().replace('-', ''));
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.group-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  color: white;
  font-size: 12px;
  font-weight: 600;

  &--sa { background: $color-group-sa; }
  &--exp { background: $color-group-exp; }
  &--aiauto { background: $color-group-ai-auto; }
  &--tca { background: $color-group-tca; }
}
</style>
