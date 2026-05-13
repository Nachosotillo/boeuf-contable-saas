import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { tasasApi } from '@/services/api'
import { fmtNum } from '@/utils'

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

  const { data: tasa } = useQuery({
    queryKey: ['tasa-bcv'],
    queryFn: () => tasasApi.actual().then(r => r.data),
    refetchInterval: 5 * 60 * 1000,
    retry: false,
  })

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-surface-50 overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="w-[220px] min-w-[220px] bg-white border-r border-surface-200 flex flex-col overflow-hidden">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-surface-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-brand-500 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold font-display">B</span>
            </div>
            <div>
              <div className="text-sm font-semibold font-display text-surface-900 leading-none">Boeuf</div>
              <div className="text-[10px] text-surface-400 leading-none mt-0.5">Contable SaaS</div>
            </div>
          </div>

          {/* Tasa BCV */}
          {tasa && (
            <div className="mt-3 flex items-center gap-1.5 text-[11px] bg-brand-50 text-brand-700 rounded-lg px-2.5 py-1.5">
              <i className="ti ti-currency-dollar text-xs" />
              <span className="font-mono font-medium">{fmtNum(tasa.tasa_usd)}</span>
              <span className="text-brand-500">Bs./USD</span>
              <span className="ml-auto text-brand-400 text-[9px]">BCV</span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map(({ section, items }) => (
            <div key={section}>
              <div className="nav-section">{section}</div>
              {items.map(({ to, icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `nav-item ${isActive ? 'active' : ''}`
                  }
                >
                  <i className={`ti ${icon} text-base`} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-surface-100 p-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 text-xs font-semibold flex items-center justify-center flex-shrink-0">
              {user?.nombre?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-surface-900 truncate">{user?.nombre}</div>
              <div className="text-[10px] text-surface-400 capitalize">{user?.rol}</div>
            </div>
            <button
              onClick={handleLogout}
              className="btn-icon text-surface-400 hover:text-danger"
              title="Cerrar sesión"
            >
              <i className="ti ti-logout text-base" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-[1400px] mx-auto page-enter">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  )
}
