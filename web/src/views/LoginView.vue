<script setup>
// C1 登录页骨架：M1 单用户 token 已内置，M3 接 POST /auth/login（T3.1）
import { useRouter } from 'vue-router'
import { ref } from 'vue'

const router = useRouter()
const username = ref('')
const password = ref('')

function login() {
  // TODO(T3.1): 调 /auth/login 换 token，失败提示；M1 直接放行
  router.replace('/')
}
</script>

<template>
  <div class="login">
    <h2>影海拾光</h2>
    <van-field v-model="username" label="账号" placeholder="账号" />
    <van-field v-model="password" label="密码" type="password" placeholder="密码" />
    <van-button type="primary" block @click="login">登录</van-button>
  </div>
</template>

<style scoped>
.login { max-width: 360px; margin: 80px auto; display: grid; gap: 16px; }
h2 { text-align: center; }
</style>
