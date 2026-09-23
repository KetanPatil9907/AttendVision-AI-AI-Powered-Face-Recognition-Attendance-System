import { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react'
import { api, clearTokens } from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('sa.user') || 'null')
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(!user)

  useEffect(() => {
    if (user) {
      setLoading(false)
      return
    }
    let active = true
    api
      .get('/auth/me')
      .then((r) => {
        if (!active) return
        setUser(r.data)
        localStorage.setItem('sa.user', JSON.stringify(r.data))
      })
      .catch(() => {})
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [user])

  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('sa:logout', onLogout)
    return () => window.removeEventListener('sa:logout', onLogout)
  }, [])

  const login = useCallback(async ({ username, password, rememberMe }) => {
    const r = await api.post('/auth/login', { username, password, remember_me: rememberMe })
    localStorage.setItem('sa.access', r.data.access)
    localStorage.setItem('sa.refresh', r.data.refresh)
    setUser(r.data.user)
    localStorage.setItem('sa.user', JSON.stringify(r.data.user))
    return r.data.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout', { refresh: localStorage.getItem('sa.refresh') })
    } catch {
      /* ignore */
    }
    clearTokens()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    const r = await api.get('/auth/me')
    setUser(r.data)
    localStorage.setItem('sa.user', JSON.stringify(r.data))
    return r.data
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      refreshUser,
      isAdmin: user?.role === 'admin',
    }),
    [user, loading, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}