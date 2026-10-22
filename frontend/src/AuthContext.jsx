import { createContext, useContext, useEffect, useState } from 'react'
import { login as requestLogin, validateSession } from './services/api'

const AuthContext = createContext(null)
export const supportedRoles = [
  'customer',
  'staff',
  'support_agent',
  'engineer',
  'manager',
  'admin',
]

export function normalizeDepartment(dept) {
  if (!dept) return null
  const d = String(dept).trim().toLowerCase()
  if (d === 'network' || d === 'network operations') return 'Network'
  if (d === 'technical' || d === 'technical support' || d === 'field engineering') return 'Technical'
  if (d === 'billing' || d === 'billing and payments' || d === 'billing & payments') return 'Billing'
  if (d === 'customer support' || d === 'support' || d === 'customer service') return 'Customer Support'
  if (d === 'operations' || d === 'management') return 'Operations'
  return String(dept).trim()
}

export function getAuthorizedDashboard(user) {
  if (!user) return '/login'
  if (user.role === 'customer') return '/customer'
  const dept = normalizeDepartment(user.department)
  if (user.role === 'manager' || user.role === 'admin' || dept === 'Operations') {
    return '/company'
  }
  if (dept === 'Network') {
    return '/company/network'
  }
  if (dept === 'Technical' || dept === 'Billing' || dept === 'Customer Support') {
    return '/company/complaints'
  }
  return '/company'
}

function clearStoredAuth() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('auth_user')
}

function getTokenExpiration(token) {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const decoded = JSON.parse(
      atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    )
    return Number.isFinite(decoded.exp) ? decoded.exp : null
  } catch {
    return null
  }
}

function isTokenExpired(token) {
  const expiration = getTokenExpiration(token)
  return expiration === null || expiration <= Date.now() / 1000
}

function readStoredAuth() {
  const token = localStorage.getItem('access_token')
  try {
    const user = JSON.parse(localStorage.getItem('auth_user'))
    if (
      !token ||
      isTokenExpired(token) ||
      !user ||
      !supportedRoles.includes(user.role)
    ) {
      clearStoredAuth()
      return { token: null, user: null }
    }
    return { token, user }
  } catch {
    clearStoredAuth()
    return { token: null, user: null }
  }
}

export function AuthProvider({ children }) {
  const [initialAuth] = useState(readStoredAuth)
  const [token, setToken] = useState(initialAuth.token)
  const [user, setUser] = useState(initialAuth.user)
  const [sessionReady, setSessionReady] = useState(!initialAuth.token)

  useEffect(() => {
    function handleUnauthorized() {
      clearStoredAuth()
      setToken(null)
      setUser(null)
      setSessionReady(true)
    }

    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [])

  useEffect(() => {
    if (!token) {
      setSessionReady(true)
      return undefined
    }

    let active = true
    const expirationTimer = window.setTimeout(() => {
      clearStoredAuth()
      setToken(null)
      setUser(null)
      setSessionReady(true)
    }, Math.max(getTokenExpiration(token) * 1000 - Date.now(), 0))
    setSessionReady(false)
    validateSession(token)
      .then((validatedUser) => {
        if (!active) return
        if (!supportedRoles.includes(validatedUser.role)) {
          clearStoredAuth()
          setToken(null)
          setUser(null)
          return
        }
        localStorage.setItem('auth_user', JSON.stringify(validatedUser))
        setUser(validatedUser)
      })
      .catch((error) => {
        if (active && error.status === 401) {
          clearStoredAuth()
          setToken(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (active) setSessionReady(true)
      })

    return () => {
      active = false
      window.clearTimeout(expirationTimer)
    }
  }, [token])

  async function login(email, password) {
    const result = await requestLogin(email, password)
    if (!supportedRoles.includes(result.user?.role)) {
      throw new Error('Unsupported user role')
    }
    localStorage.setItem('access_token', result.access_token)
    localStorage.setItem('auth_user', JSON.stringify(result.user))
    setToken(result.access_token)
    setUser(result.user)
    setSessionReady(true)
    return result.user
  }

  function logout() {
    clearStoredAuth()
    setToken(null)
    setUser(null)
    setSessionReady(true)
  }

  const isCustomer = user?.role === 'customer'
  const isEmployee = Boolean(user && user.role !== 'customer')
  const department = normalizeDepartment(user?.department)

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        sessionReady,
        login,
        logout,
        isCustomer,
        isEmployee,
        department,
      }}
    >
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