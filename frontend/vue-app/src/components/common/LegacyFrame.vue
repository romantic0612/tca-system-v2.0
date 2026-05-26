<template>
  <section class="legacy-shell">
    <iframe
      ref="frameRef"
      class="legacy-frame"
      :src="src"
      :title="title"
    />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  title: string;
  src: string;
  tag?: string;
}>();

const frameRef = ref<HTMLIFrameElement | null>(null);
</script>

<style scoped lang="scss">
.legacy-shell {
  min-height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #ffffff;
}

.legacy-frame {
  width: 100%;
  height: 100vh;
  border: 0;
  display: block;
  background: #ffffff;
}
</style>
