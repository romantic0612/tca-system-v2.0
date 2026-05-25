<template>
  <main class="admin-view admin-page">
    <section class="admin-shell">
      <header>
        <h1>TCA-System 管理后台</h1>
        <GradientButton>新建学生</GradientButton>
      </header>
      <div class="stats">
        <div class="stat stat--sa"><span>SA</span><strong>0</strong></div>
        <div class="stat stat--exp"><span>EXP</span><strong>0</strong></div>
        <div class="stat stat--tca"><span>TCA</span><strong>0</strong></div>
        <div class="stat stat--aiauto"><span>AI-AUTO</span><strong>0</strong></div>
      </div>
      <el-table :data="[]">
        <el-table-column prop="student_id" label="学号" />
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="group" label="组别" />
      </el-table>
    </section>
  </main>
</template>

<script setup lang="ts">
import GradientButton from '@/components/common/GradientButton.vue';
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.admin-view {
  padding: 24px;
}

.admin-shell {
  width: min(1180px, 100%);
  min-height: calc(100vh - 48px);
  margin: 0 auto;
  padding: 24px;
  background: white;
  border-radius: $radius-card;
  box-shadow: $shadow-teacher-card;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 20px 0;
}

.stat {
  padding: 16px;
  border-radius: 14px;
  background: #f8f9fa;
  border-left: 4px solid $color-group-sa;

  strong {
    display: block;
    margin-top: 8px;
    font-size: 28px;
  }

  &--exp { border-left-color: $color-group-exp; }
  &--tca { border-left-color: $color-group-tca; }
  &--aiauto { border-left-color: $color-group-ai-auto; }
}
</style>
