<script setup>
// C1 登录（T3.1b）：POST /auth/login → 存 token → 进主页
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { auth } from '../api/http'

const router = useRouter()
const username = ref('dev')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function login() {
  loading.value = true
  error.value = ''
  try {
    // 登录接口本身不鉴权，用裸 axios 避免 401 拦截器干扰
    const resp = await axios.post('/api/v1/auth/login', {
      username: username.value,
      password: password.value,
    })
    if (resp.data.code === 0) {
      auth.save(resp.data.data.access_token, resp.data.data.refresh_token)
      router.replace('/')
    } else {
      error.value = resp.data.message
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请检查网络'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <h2>影海拾光</h2>
    <p class="sub">把刷过的视频，攒成你的知识星空</p>
    <van-field v-model="username" label="账号" placeholder="账号" />
    <van-field v-model="password" label="密码" type="password" placeholder="密码" @keyup.enter="login" />
    <van-button type="primary" block :loading="loading" @click="login">登录</van-button>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.login { max-width: 360px; margin: 80px auto; display: grid; gap: 16px; }
h2 { text-align: center; margin-bottom: -8px; }
.sub { text-align: center; color: #888; font-size: 13px; }
.error { color: #ee0a24; font-size: 13px; text-align: center; }
</style>
