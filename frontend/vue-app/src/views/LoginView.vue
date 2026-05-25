<template>
  <main class="login-view brand-page">
    <section class="login-hero">
      <h1>TCA-System</h1>
      <p>基于人机协同的初中数学智能学习系统</p>
    </section>

    <el-card class="login-card">
      <template #header>用户登录</template>
      <el-form @submit.prevent="submit">
        <el-form-item label="账号">
          <el-input v-model="form.userId" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <GradientButton class="login-button" native-type="submit" :disabled="auth.loading">
          {{ auth.loading ? '登录中...' : '登录' }}
        </GradientButton>
      </el-form>
    </el-card>
  </main>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import GradientButton from '@/components/common/GradientButton.vue';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const auth = useAuthStore();
const form = reactive({ userId: '', password: '' });

async function submit() {
  try {
    const user = await auth.login(form.userId, form.password);
    if (!user?.role) throw new Error('登录响应缺少角色信息');
    const target = user.role === 'student' ? '/student' : user.role === 'teacher' ? '/teacher' : '/admin';
    await router.push(target);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败');
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.login-view {
  display: grid;
  place-items: center;
  gap: 28px;
  padding: 40px 20px;
}

.login-hero {
  color: white;
  text-align: center;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);

  h1 {
    font-size: 42px;
    font-weight: 800;
  }

  p {
    margin-top: 10px;
    font-size: 18px;
  }
}

.login-card {
  width: min(420px, 100%);
  border-radius: $radius-card;
  box-shadow: $shadow-card;
}

.login-button {
  width: 100%;
}
</style>
