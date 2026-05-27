<template>
  <main class="login-view">
    <section class="login-header" aria-label="系统介绍">
      <span class="brand-mark">ZR</span>
      <h1>智融</h1>
      <p>教师可控自适应学习系统</p>
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
    </el-card>

    <section class="demo-accounts" aria-label="快捷登录">
      <span class="accounts-title">快捷登录</span>
      <div class="account-grid">
        <button type="button" class="account-item" @click="fill('20240003', '123456')">
          <strong>TCA学生</strong>
          <span>20240003</span>
        </button>
        <button type="button" class="account-item" @click="fill('100001', 'teacher123')">
          <strong>教师</strong>
          <span>100001</span>
        </button>
        <button type="button" class="account-item admin" @click="fill('900001', 'admin123')">
          <strong>管理员</strong>
          <span>900001</span>
        </button>
      </div>
    </section>

    <footer class="login-footer">智融 · 华东师范大学 · v2.0</footer>
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 22px;
  padding: 32px 20px;
  background:
    radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.18), transparent 26%),
    linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-header {
  text-align: center;
  color: #fff;
  text-shadow: 0 3px 12px rgba(21, 28, 56, 0.22);

  .brand-mark {
    display: inline-grid;
    place-items: center;
    width: 54px;
    height: 54px;
    margin-bottom: 10px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.34);
    color: #fff;
    font-weight: 800;
    letter-spacing: 1px;
  }

  h1 {
    margin: 0 0 8px;
    font-size: 42px;
    font-weight: 800;
    letter-spacing: 4px;
  }

  p {
    margin: 0;
    font-size: 16px;
    letter-spacing: 2px;
    color: rgba(255, 255, 255, 0.9);
  }
}

.login-card {
  width: min(400px, 100%);
  border: 0;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(18, 24, 50, 0.3);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  strong {
    font-size: 18px;
  }

  span {
    color: #8a94a6;
    font-size: 13px;
  }
}

.login-button {
  width: 100%;
  height: 46px;
  margin-top: 2px;
  border: 0;
  border-radius: 12px;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #2e86ab 0%, #4caf50 100%);
  box-shadow: 0 8px 22px rgba(46, 134, 171, 0.32);
}

.demo-accounts {
  width: min(400px, 100%);
}

.accounts-title {
  display: block;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  text-align: center;
  letter-spacing: 1px;
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
}

.account-item {
  min-width: 0;
  padding: 12px 6px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 12px;
  background: rgba(46, 134, 171, 0.2);
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    background: rgba(46, 134, 171, 0.34);
  }

  strong,
  span {
    display: block;
  }

  strong {
    font-size: 14px;
    margin-bottom: 4px;
  }

  span {
    color: rgba(255, 255, 255, 0.72);
    font-size: 12px;
  }

  &.admin {
    background: rgba(118, 75, 162, 0.26);
  }
}

.login-footer {
  margin-top: 2px;
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
}

@media (max-width: 520px) {
  .login-view {
    padding: 24px 14px;
  }

  .login-header h1 {
    font-size: 36px;
  }

  .account-grid {
    grid-template-columns: 1fr;
  }
}
</style>
