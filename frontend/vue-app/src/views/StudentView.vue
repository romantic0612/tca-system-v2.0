<template>
  <main class="student-view brand-page">
    <section class="student-shell brand-card">
      <header class="student-topbar">
        <strong>TCA-System</strong>
        <div>
          <GroupBadge group="TCA" />
        </div>
      </header>

      <section class="question-panel">
        <strong>第 3/10 题</strong>
        <p>已知三角形 ABC 中，角 A=50 度，角 B=70 度，求角 C 的度数。</p>
      </section>

      <section class="chat-panel">
        <MessageBubble role="assistant" agent="Guide" content="我们先看看题目给出的已知条件。" time="09:30" />
        <MessageBubble role="user" content="我不会" time="09:31" />
        <MessageBubble role="teacher" content="注意已知条件中两个角的关系，想想它们加起来是多少度？" time="09:32" />
      </section>

      <footer class="input-panel">
        <el-input placeholder="输入消息与 AI 对话..." />
        <GradientButton>发送</GradientButton>
      </footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import GradientButton from '@/components/common/GradientButton.vue';
import GroupBadge from '@/components/common/GroupBadge.vue';
import MessageBubble from '@/components/common/MessageBubble.vue';
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.student-view {
  padding: 24px;
}

.student-shell {
  width: min(1180px, 100%);
  min-height: calc(100vh - 48px);
  margin: 0 auto;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  overflow: hidden;
}

.student-topbar,
.question-panel,
.input-panel {
  padding: 16px 24px;
  border-bottom: 1px solid $border-default;
}

.student-topbar,
.input-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: $chat-bg-gradient;
  overflow-y: auto;
}
</style>
