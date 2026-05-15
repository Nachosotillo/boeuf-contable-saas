import { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { tasasApi, empresaApi } from '@/services/api'
import { fmtNum, extractError } from '@/utils'
import { Modal, Field, Spinner } from '@/components/Common'
import type { Empresa } from '@/types'

interface NavItem {
  to: string
  icon: string
  label: string
}

const NAV: { section: string; items: NavItem[] }[] = [
  {
    section: 'Principal',
    items: [{ to: '/dashboard', icon: 'ti-layout-dashboard', label: 'Dashboard' }],
  },
  {
    section: 'Contabilidad',
    items: [
      { to: '/diario',   icon: 'ti-notebook',   label: 'Diario General' },
      { to: '/ajustes',  icon: 'ti-adjustments', label: 'Ajustes' },
      { to: '/catalogo', icon: 'ti-list',         label: 'Catálogo' },
      { to: '/mayor',    icon: 'ti-book',         label: 'Mayor General' },
    ],
  },
  {
    section: 'Reportes',
    items: [
      { to: '/balance',          icon: 'ti-scale',          label: 'Balance comp.' },
      { to: '/balance-ajustado', icon: 'ti-file-analytics', label: 'Balance ajustado' },
      { to: '/resultado',        icon: 'ti-chart-bar',      label: 'Estado resultado' },
      { to: '/situacion',        icon: 'ti-building-bank',  label: 'Situación fin.' },
    ],
  },
  {
    section: 'Fiscal',
    items: [
      { to: '/iva',        icon: 'ti-receipt',       label: 'Libros IVA' },
      { to: '/igtf',       icon: 'ti-currency-dollar',label: 'IGTF' },
      { to: '/retenciones',icon: 'ti-file-invoice',  label: 'Ret. ISLR' },
      { to: '/seniat',     icon: 'ti-file-text',     label: 'Exportar SENIAT' },
    ],
  },
  {
    section: 'Operaciones',
    items: [
      { to: '/nomina',     icon: 'ti-users',             label: 'Nómina + ISLR' },
      { to: '/provisiones',icon: 'ti-piggy-bank',        label: 'Provisiones' },
      { to: '/inventario', icon: 'ti-package',            label: 'Inventario MP' },
      { to: '/activos',    icon: 'ti-building-factory',  label: 'Activos Fijos' },
    ],
  },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [openSettings, setOpenSettings] = useState(false)

  const { data: empresa, isLoading: loadEmp } = useQuery<Empresa>({
    queryKey: ['mi-empresa'],
    queryFn: () => empresaApi.me().then(r => r.data),
  })

  const { data: tasa } = useQuery({
    queryKey: ['tasa-bcv'],
    queryFn: () => tasasApi.actual().then(r => r.data),
    refetchInterval: 5 * 60 * 1000,
    retry: false,
  })

  const { register, handleSubmit, reset } = useForm<Partial<Empresa>>()

  useEffect(() => { if (empresa) reset(empresa) }, [empresa, reset])

  const editEmp = useMutation({
    mutationFn: (data: Partial<Empresa>) => empresaApi.actualizar(data),
    onSuccess: () => {
      toast.success('Empresa actualizada ✓')
      qc.invalidateQueries({ queryKey: ['mi-empresa'] })
      setOpenSettings(false)
    },
    onError: (err) => toast.error(extractError(err)),
  })

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-surface-50 overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="w-[240px] min-w-[240px] bg-white border-r border-surface-200 flex flex-col overflow-hidden">
        {/* Logo & Empresa */}
        <div className="px-4 py-4 border-b border-surface-100 bg-surface-50/30">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center shadow-sm shadow-brand-200">
                <span className="text-white text-sm font-bold font-display">B</span>
              </div>
              <div className="min-w-0">
                <div className="text-sm font-bold font-display text-surface-900 leading-tight truncate">
                  {empresa?.nombre_razon_social || 'Boeuf Contable'}
                </div>
                <div className="text-[10px] text-brand-600 font-bold tracking-wider mt-0.5 uppercase">
                  {empresa?.rif || 'J-00000000-0'}
                </div>
              </div>
            </div>
            <button onClick={() => setOpenSettings(true)} className="btn-icon btn-sm text-surface-400 hover:text-brand-600">
              <i className="ti ti-settings text-base" />
            </button>
          </div>

          {/* Tasa BCV */}
          {tasa && (
            <div className="mt-4 flex items-center gap-1.5 text-[11px] bg-white border border-brand-100 text-brand-700 rounded-lg px-2.5 py-1.5 shadow-sm">
              <i className="ti ti-currency-dollar text-xs text-brand-500" />
              <span className="font-mono font-bold">{fmtNum(tasa.tasa_usd)}</span>
              <span className="text-brand-400 font-medium">Bs./USD</span>
              <span className="ml-auto text-[9px] font-bold bg-brand-100 px-1 rounded text-brand-600">BCV</span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 custom-scrollbar">
          {NAV.map(({ section, items }) => (
            <div key={section} className="mb-4">
              <div className="px-5 mb-1.5 text-[10px] font-bold text-surface-400 uppercase tracking-widest">{section}</div>
              {items.map(({ to, icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-5 py-2 text-sm font-medium transition-all border-r-2 ${
                      isActive 
                        ? 'bg-brand-50 text-brand-700 border-brand-600' 
                        : 'text-surface-600 border-transparent hover:bg-surface-50 hover:text-surface-900'
                    }`
                  }
                >
                  <i className={`ti ${icon} text-lg ${to.includes('active') ? 'text-brand-500' : ''}`} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-surface-100 p-4 bg-surface-50/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-100 text-brand-700 text-sm font-bold flex items-center justify-center flex-shrink-0 border border-brand-200">
              {user?.nombre?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-surface-900 truncate">{user?.nombre}</div>
              <div className="text-[10px] text-surface-500 font-medium capitalize">{user?.rol?.replace('_', ' ')}</div>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 text-surface-400 hover:text-danger hover:bg-danger/10 rounded-lg transition-all"
              title="Cerrar sesión"
            >
              <i className="ti ti-logout text-lg" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden shadow-2xl shadow-surface-900/5 z-10">
        <div className="flex-1 overflow-y-auto bg-surface-50">
          <div className="p-8 max-w-[1400px] mx-auto page-enter">
            <Outlet />
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      <Modal open={openSettings} onClose={() => setOpenSettings(false)} title="Configuración de la Empresa"
        footer={<><button onClick={() => setOpenSettings(false)} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => editEmp.mutate(d))} disabled={editEmp.isPending} className="btn-primary">Guardar Cambios</button></>}>
        {loadEmp ? <Spinner /> : (
          <div className="space-y-4">
            <Field label="Razón Social"><input className="input font-bold" {...register('nombre_razon_social')} /></Field>
            <Field label="RIF (Ej: J-12345678-0)"><input className="input font-mono" {...register('rif')} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Tipo de Persona"><select className="input" {...register('tipo_persona')}><option value="Jurídica">Jurídica</option><option value="Natural">Natural</option></select></Field>
              <Field label="Tipo Contribuyente"><select className="input" {...register('tipo_contribuyente')}><option value="Ordinario">Ordinario</option><option value="SPE">Sujeto Pasivo Especial (SPE)</option></select></Field>
            </div>
            <Field label="Dirección Fiscal"><textarea className="input text-xs" rows={2} {...register('direccion')} /></Field>
          </div>
        )}
      </Modal>
    </div>
  )
}
