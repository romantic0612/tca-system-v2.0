import { defineStore } from 'pinia';
import { http } from '@/api/http';

export type UserRole = 'student' | 'teacher' | 'admin_exp' | 'admin_sys';

export interface UserInfo {
  user_id: number | string;
  role: UserRole;
  name?: string;
  condition?: 'SA' | 'EXP' | 'AI-AUTO' | 'TCA';
}

interface AuthResponse {
  success?: boolean;
  error?: string;
  logged_in?: boolean;
  user_id?: number | string;
  role?: UserRole;
  user_info?: Partial<UserInfo>;
  student_name?: string;
  experiment_group?: UserInfo['condition'];
}

function normalizeUserInfo(data: AuthResponse): UserInfo | null {
  if (data.user_info?.user_id !== undefined && data.user_info.role) {
    return data.user_info as UserInfo;
  }

  if (data.user_id !== undefined && data.role) {
    return {
      user_id: data.user_id,
      role: data.role,
      name: data.student_name,
      condition: data.experiment_group,
    };
  }

  return null;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as UserInfo | null,
    loading: false,
  }),
  actions: {
    async login(userId: string, password: string) {
      this.loading = true;
      try {
        const { data } = await http.post('/auth/login', {
          user_id: userId,
          password,
        });
        if (!data.success) throw new Error(data.error || '登录失败');
        const user = normalizeUserInfo(data);
        if (!user) throw new Error('登录响应缺少用户信息');
        this.user = user;
        return this.user;
      } finally {
        this.loading = false;
      }
    },
    async check() {
      const { data } = await http.get('/auth/check');
      this.user = data.logged_in ? normalizeUserInfo(data) : null;
      return this.user;
    },
    async logout() {
      await http.post('/auth/logout');
      this.user = null;
    },
  },
});
