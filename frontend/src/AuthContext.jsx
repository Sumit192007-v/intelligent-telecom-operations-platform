import { createContext, useContext, useState } from 'react'
import { login as requestLogin } from './services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('auth_user'))
    } catch {
      return null
    }
  })

  async function login(email, password) {
    const result = await requestLogin(email, password)
    localStorage.setItem('access_token', result.access_token)
    localStorage.setItem('auth_user', JSON.stringify(result.user))
    setToken(result.access_token)
    setUser(result.user)
    return result.user
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('auth_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}