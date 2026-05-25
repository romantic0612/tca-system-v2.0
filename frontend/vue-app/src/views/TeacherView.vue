<template>
  <main class="teacher-view teacher-page">
    <section class="teacher-shell">
      <aside class="student-list">
        <h2>待处理请求</h2>
        <div class="pending-card">
          <GroupBadge group="TCA" />
          <strong>王芳 第 3 题</strong>
          <p>系统检测到 L1 触发，建议教师查看。</p>
        </div>
      </aside>
      <section class="session-panel">
        <header>
          <h1>王芳</h1>
          <AgentBadge agent="Guide" />
        </header>
        <div class="history">
          <MessageBubble role="user" content="我不会" />
          <MessageBubble role="assistant" agent="Guide" content="我们先想想这道题考察了什么知识点。" />
        </div>
        <div class="override-panel">
          <el-select model-value="Tutor">
            <el-option label="Guide" value="Guide" />
            <el-option label="Tutor" value="Tutor" />
          </el-select>
          <el-input type="textarea" placeholder="输入要发送给学生的解释或提示..." />
          <GradientButton>发送</GradientButton>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import AgentBadge from '@/components/common/AgentBadge.vue';
import GradientButton from '@/components/common/GradientButton.vue';
import GroupBadge from '@/components/common/GroupBadge.vue';
import MessageBubble from '@/components/common/MessageBubble.vue';
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.teacher-view {
  padding: 24px;
}

.teacher-shell {
  width: min(1280px, 100%);
  min-height: calc(100vh - 48px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 360px 1fr;
  background: white;
  border-radius: $radius-card;
  box-shadow: $shadow-teacher-card;
  overflow: hidden;
}

.student-list,
.session-panel {
  padding: 20px;
}

.student-list {
  border-right: 1px solid $border-default;
}

.pending-card {
  margin-top: 16px;
  padding: 16px;
  border-left: 4px solid $accent-red;
  border-radius: 12px;
  background: #fff5f5;
  animation: pulse 1.6s ease-in-out infinite;
}

.session-panel {
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 16px;
}

.history {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: $chat-bg-gradient;
  border-radius: 16px;
}

.override-panel {
  display: grid;
  grid-template-columns: 130px 1fr auto;
  gap: 12px;
  align-items: start;
}
</style>
