<template>
  <main class="login-view">
    <section class="login-copy">
      <el-tag effect="dark" type="success">Vue3 + Element Plus</el-tag>
      <h1>TCA-System</h1>
      <p>教师可控的自适应数学学习系统</p>
      <div class="feature-list">
        <span>四组实验</span>
        <span>AI-AUTO 切换</span>
        <span>教师 Override</span>
        <span>实验数据导出</span>
      </div>
    </section>

    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="card-header">
          <strong>用户登录</strong>
          <span>请输入测试账号</span>
        </div>
      </template>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="账号">
          <el-input
            v-model.trim="form.userId"
            size="large"
            placeholder="学生学号 / 教师工号 / 管理员工号"
            autocomplete="username"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            placeholder="请输入密码"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          class="login-button"
          size="large"
          type="primary"
          native-type="submit"
          :loading="auth.loading"
        >
          登录
        </el-button>
      </el-form>

      <el-divider />
      <div class="demo-accounts">
        <button type="button" @click="fill('20240003', '123456')">TCA 学生</button>
        <button type="button" @click="fill('100001', 'teacher123')">教师</button>
        <button type="button" @click="fill('900001', 'admin123')">管理员</button>
      </div>
    </el-card>
  </main>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const auth = useAuthStore();
const form = reactive({ userId: '', password: '' });

function fill(userId: string, password: string) {
  form.userId = userId;
  form.password = password;
}

async function submit() {
  if (!form.userId || !form.password) {
    ElMessage.warning('请先输入账号和密码');
    return;
  }

  try {
    const user = await auth.login(form.userId, form.password);
    if (!user?.role) throw new Error('登录响应缺少角色信息');
    const target = user.role === 'student'
      ? '/student'
      : user.role === 'teacher'
        ? '/teacher'
        : '/admin';
    ElMessage.success('登录成功');
    await router.push(target);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败');
  }
}
</script>

<style scoped lang="scss">
.login-view {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(360px, 460px);
  align-items: center;
  gap: 44px;
  padding: 56px min(7vw, 92px);
  background:
    linear-gradient(135deg, rgba(42, 143, 234, 0.88), rgba(46, 184, 124, 0.82)),
    #eef2f7;
}

.login-copy {
  color: #fff;

  h1 {
    margin: 22px 0 10px;
    font-size: 52px;
    font-weight: 800;
  }

  p {
    margin: 0 0 26px;
    font-size: 22px;
  }
}

.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;

  span {
    padding: 9px 13px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.36);
  }
}

.login-card {
  border-radius: 18px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;

  span {
    color: #8a94a6;
    font-size: 13px;
  }
}

.login-button {
  width: 100%;
}

.demo-accounts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;

  button {
    height: 34px;
    border: 1px solid #d8dee9;
    border-radius: 8px;
    background: #fff;
    cursor: pointer;
  }
}

@media (max-width: 820px) {
  .login-view {
    grid-template-columns: 1fr;
    padding: 28px 18px;
  }

  .login-copy h1 {
    font-size: 40px;
  }
}
</style>
