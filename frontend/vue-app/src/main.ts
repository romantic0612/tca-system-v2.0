import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import '@/styles/element-overrides.scss';
import '@/styles/global.scss';
import App from './App.vue';
import router from './router';

createApp(App)
  .use(createPinia())
  .use(router)
  .use(ElementPlus)
  .mount('#app');
