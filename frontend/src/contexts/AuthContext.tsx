import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import type { Usuario } from '@/types'

interface AuthState {
  user: Usuario | null
  token: string | null
  isAuthenticated: boolean
  login: (token: string, user: Usuario) => void
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null, token: null, isAuthenticated: false,
  login: () => {}, logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('boeuf_token'))
  const [user, setUser] = useState<Usuario | null>(() => {
    const stored = localStorage.getItem('boeuf_user')
    return stored ? JSON.parse(stored) : null
  })

  const login = (newToken: string, newUser: Usuario) => {
    localStorage.setItem('boeuf_token', newToken)
    localStorage.setItem('boeuf_user', JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
  }

  const logout = () => {
    localStorage.removeItem('boeuf_token')
    localStorage.removeItem('boeuf_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token && !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
