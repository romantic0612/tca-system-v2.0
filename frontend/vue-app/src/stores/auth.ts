import { defineStore } from 'pinia';
import { http } from '@/api/http';

export type UserRole = 'student' | 'teacher' | 'admin_exp' | 'admin_sys';

export interface UserInfo {
  user_id: number | string;
  role: UserRole;
  name?: string;
  condition?: 'SA' | 'EXP' | 'AI-AUTO' | 'TCA';
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
        this.user = data.user_info as UserInfo;
        return this.user;
      } finally {
        this.loading = false;
      }
    },
    async check() {
      const { data } = await http.get('/auth/check');
      this.user = data.logged_in ? (data.user_info as UserInfo) : null;
      return this.user;
    },
    async logout() {
      await http.post('/auth/logout');
      this.user = null;
    },
  },
});
