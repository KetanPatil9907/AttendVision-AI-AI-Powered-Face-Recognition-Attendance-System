import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

let refreshing = null

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sa.access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { response, config } = error
    const status = response?.status
    if (
      status === 401 &&
      !config?._retried &&
      !String(config?.url || '').includes('/auth/login') &&
      !String(config?.url || '').includes('/auth/refresh')
    ) {
      config._retried = true
      try {
        if (!refreshing) {
          refreshing = api
            .post('/auth/refresh', { refresh: localStorage.getItem('sa.refresh') })
            .then((r) => {
              localStorage.setItem('sa.access', r.data.access)
              if (r.data.refresh) localStorage.setItem('sa.refresh', r.data.refresh)
              return r.data.access
            })
            .finally(() => {
              refreshing = null
            })
        }
        await refreshing
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${localStorage.getItem('sa.access')}`
        return api(config)
      } catch (refreshError) {
        localStorage.removeItem('sa.access')
        localStorage.removeItem('sa.refresh')
        localStorage.removeItem('sa.user')
        window.dispatchEvent(new Event('sa:logout'))
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  },
)

export function normalizeError(err) {
  const data = err?.response?.data
  if (typeof data?.message === 'string' && data.message) return data.message
  if (data?.errors) {
    const parts = Object.entries(data.errors).map(([key, value]) => {
      const text = Array.isArray(value) ? value.join(', ') : String(value)
      return `${key}: ${text}`
    })
    if (parts.length) return parts.join(' • ')
  }
  return err?.message || 'Something went wrong.'
}

export function unwrapList(r) {
  return Array.isArray(r?.data) ? r.data : (r?.data?.results || [])
}

export function setTokens(access, refresh) {
  localStorage.setItem('sa.access', access)
  if (refresh) localStorage.setItem('sa.refresh', refresh)
}

export function clearTokens() {
  localStorage.removeItem('sa.access')
  localStorage.removeItem('sa.refresh')
  localStorage.removeItem('sa.user')
}