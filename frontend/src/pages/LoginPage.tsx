import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { authApi } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { extractError } from '@/utils'
import type { TokenResponse } from '@/types'

interface LoginForm { email: string; password: string }

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>()

  const onSubmit = async (data: LoginForm) => {
    setLoading(true)
    try {
      const res = await authApi.login(data.email, data.password)
      const body: TokenResponse = res.data
      login(body.access_token, body.usuario)
      toast.success(`Bienvenido, ${body.usuario.nombre}`)
      navigate('/dashboard')
    } catch (err) {
      toast.error(extractError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-50 via-brand-50 to-surface-100 flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-brand-100 rounded-full opacity-40 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-brand-50 rounded-full opacity-60 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Card */}
        <div className="card p-8 animate-slide-up">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center shadow-sm">
              <span className="text-white font-bold font-display text-lg">B</span>
            </div>
            <div>
              <h1 className="text-xl font-bold font-display text-surface-900">Boeuf Contable</h1>
              <p className="text-xs text-surface-400">Sistema Contable SaaS Venezuela</p>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-surface-800 mb-1">Iniciar sesión</h2>
          <p className="text-sm text-surface-500 mb-6">Accede a tu sistema contable</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Correo electrónico</label>
              <input
                type="email"
                className={`input ${errors.email ? 'input-error' : ''}`}
                placeholder="contador@empresa.com"
                {...register('email', { required: 'Campo requerido' })}
              />
              {errors.email && <p className="text-xs text-danger mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="label">Contraseña</label>
              <input
                type="password"
                className={`input ${errors.password ? 'input-error' : ''}`}
                placeholder="••••••••"
                {...register('password', { required: 'Campo requerido', minLength: { value: 6, message: 'Mínimo 6 caracteres' } })}
              />
              {errors.password && <p className="text-xs text-danger mt-1">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-2.5 text-base mt-2"
            >
              {loading ? (
                <><i className="ti ti-loader-2 animate-spin" /> Verificando...</>
              ) : (
                <><i className="ti ti-login" /> Entrar</>
              )}
            </button>
          </form>

          {/* Regulaciones note */}
          <div className="mt-6 pt-4 border-t border-surface-100">
            <div className="flex flex-wrap gap-1.5">
              {['IVA 16%', 'ISLR D.1808', 'IGTF 3%', 'Prot. Pensiones', 'SENIAT'].map(tag => (
                <span key={tag} className="badge-gray text-[10px]">{tag}</span>
              ))}
            </div>
            <p className="text-[10px] text-surface-400 mt-2">Cumple con regulaciones tributarias venezolanas vigentes 2025</p>
          </div>
        </div>
      </div>
    </div>
  )
}
