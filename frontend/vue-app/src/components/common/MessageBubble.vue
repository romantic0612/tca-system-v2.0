<template>
  <div class="message-bubble" :class="`message-bubble--${role}`">
    <AgentBadge v-if="role === 'assistant' && agent" :agent="agent" />
    <div class="message-bubble__content">{{ content }}</div>
    <span class="message-bubble__time">{{ time }}</span>
  </div>
</template>

<script setup lang="ts">
import AgentBadge from './AgentBadge.vue';

defineProps<{
  role: 'user' | 'assistant' | 'system' | 'teacher';
  content: string;
  time?: string;
  agent?: 'Guide' | 'Tutor' | 'Evaluator';
}>();
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.message-bubble {
  max-width: 80%;
  padding: 12px 18px;
  animation: messageIn 0.3s ease forwards;

  &--user {
    align-self: flex-end;
    background: $user-bubble-gradient;
    color: white;
    border-radius: 18px 18px 4px 18px;
  }

  &--assistant {
    align-self: flex-start;
    background: white;
    border: 2px solid $border-default;
    border-radius: 18px 18px 18px 4px;
  }

  &--system {
    align-self: center;
    max-width: 90%;
    border: 1px dashed $brand-primary-1;
    border-radius: 12px;
    background: rgba(102, 126, 234, 0.1);
    color: $brand-primary-1;
    text-align: center;
  }

  &--teacher {
    align-self: flex-start;
    max-width: 88%;
    border-left: 4px solid $accent-orange;
    border-radius: 18px 18px 18px 4px;
    background: #fffaf0;
  }

  &__content {
    margin-top: 6px;
    line-height: 1.6;
  }

  &__time {
    display: block;
    margin-top: 4px;
    font-size: 11px;
    opacity: 0.65;
    text-align: right;
  }
}
</style>
