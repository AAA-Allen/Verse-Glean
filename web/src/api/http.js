import axios from 'axios'

/** 统一响应 {code, message, data}；code!==0 抛业务错误（docs/API.md §1/§2）。 */
const http = axios.create({ baseURL: '/api/v1', timeout: 30000 })

export const auth = {
  // M1 单用户固定 token；TODO(T3.1): JWT + localStorage 管理 + 401 跳登录
  token: 'dev-single-user-token',
}

http.interceptors.request.use((config) => {
  config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

http.interceptors.response.use(
  (resp) => {
    if (resp.data.code !== 0) return Promise.reject(new Error(resp.data.message))
    return resp.data.data
  },
  (err) => {
    if (err.response?.status === 401) auth.token = ''
    return Promise.reject(err)
  },
)

export default http
