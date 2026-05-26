import { createRouter, createWebHistory } from 'vue-router';
import LoginView from '@/views/LoginView.vue';
import StudentView from '@/views/StudentView.vue';
import TeacherView from '@/views/TeacherView.vue';
import AdminView from '@/views/AdminView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', alias: '/login.html', component: LoginView },
    { path: '/student', alias: '/student.html', component: StudentView },
    { path: '/teacher', alias: '/teacher.html', component: TeacherView },
    { path: '/admin', alias: '/admin.html', component: AdminView },
  ],
});

export default router;
