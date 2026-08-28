import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Vant from 'vant'
import 'vant/lib/index.css'

import App from './App.vue'
import LoginView from './views/LoginView.vue'
import CapsuleListView from './views/CapsuleListView.vue'
import CapsuleDetailView from './views/CapsuleDetailView.vue'
import GraphView from './views/GraphView.vue'
import { auth } from './api/http'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/', component: CapsuleListView },
    { path: '/capsules/:id', component: CapsuleDetailView },
    { path: '/graph', component: GraphView },
  ],
})

// C1 登录守卫：M1 单用户 token 存在即放行；M3 换 JWT + 过期刷新
router.beforeEach((to) => {
  if (to.path !== '/login' && !auth.token) return '/login'
})

createApp(App).use(router).use(Vant).mount('#app')
