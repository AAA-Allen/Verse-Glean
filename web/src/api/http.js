import axios from 'axios'

/** 统一响应 {code, message, data}；JWT 存储 + 401 自动刷新/登出（T3.1b）。 */
const http = axios.create({ baseURL: '/api/v1', timeout: 30000 })

const TOKEN_KEY = 'yhsg_access'
const REFRESH_KEY = 'yhsg_refresh'

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY) || ''
  },
  get refreshToken() {
    return localStorage.getItem(REFRESH_KEY) || ''
  },
  save(access, refresh) {
    localStorage.setItem(TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    location.href = '/login'
  },
}

http.interceptors.request.use((config) => {
  if (auth.token) config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

let refreshing = null

http.interceptors.response.use(
  (resp) => {
    if (resp.data.code !== 0) return Promise.reject(new Error(resp.data.message))
    return resp.data.data
  },
  async (err) => {
    const original = err.config
    // 401 且有 refresh token：静默续期一次后重放原请求
    if (err.response?.status === 401 && auth.refreshToken && !original._retried) {
      refreshing =
        refreshing ||
        axios.post('/api/v1/auth/refresh', { refresh_token: auth.refreshToken })
      try {
        const resp = await refreshing
        refreshing = null
        if (resp.data.code === 0) {
          auth.save(resp.data.data.access_token, resp.data.data.refresh_token)
          original._retried = true
          return http(original)
        }
      } catch {
        refreshing = null
      }
      auth.clear()
    }
    if (err.response?.status === 401) auth.clear()
    return Promise.reject(err)
  },
)

export default http
