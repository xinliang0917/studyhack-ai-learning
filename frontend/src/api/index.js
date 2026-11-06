import axios from 'axios'
import { clearToken } from '../utils/token'

const instance = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

instance.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers['X-Auth-Token'] = token
    config.params = { ...(config.params || {}), access_token: token }
    document.cookie = `app_token=${token}; path=/; SameSite=Lax`
  }
  return config
})

instance.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      clearToken()
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default instance
