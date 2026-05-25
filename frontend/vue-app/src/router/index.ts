import { createRouter, createWebHistory } from 'vue-router';
import LoginView from '@/views/LoginView.vue';
import StudentView from '@/views/StudentView.vue';
import TeacherView from '@/views/TeacherView.vue';
import AdminView from '@/views/AdminView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginView },
    { path: '/student', component: StudentView },
    { path: '/teacher', component: TeacherView },
    { path: '/admin', component: AdminView },
  ],
});

export default router;
