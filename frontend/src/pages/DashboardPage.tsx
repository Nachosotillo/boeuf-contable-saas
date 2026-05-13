import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { reportesApi, asientosApi, tasasApi } from '@/services/api'
import { fmtBs, fmtNum, MESES, mesActual } from '@/utils'
import type { EstadoResultado, AsientoOut } from '@/types'
import { Link } from 'react-router-dom'

function MetricCard({
  label, value, sub, icon, color = 'text-surface-900'
}: { label: string; value: string; sub?: string; icon: string; color?: string }) {
  return (
    <div className="metric-card">
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        <i className={`ti ${icon} text-surface-300 text-lg`} />
      </div>
      <div className={`metric-value ${color}`}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  )
}

export default function DashboardPage() {
  const mes = mesActual()

  const { data: resultado } = useQuery<EstadoResultado>({
    queryKey: ['estado-resultado', mes],
    queryFn: () => reportesApi.estadoResultado(mes).then(r => r.data),
  })

  const { data: asientos } = useQuery<AsientoOut[]>({
    queryKey: ['asientos-recientes'],
    queryFn: () => asientosApi.listar({ limit: 5 }).then(r => r.data),
  })

  const { data: tasa } = useQuery({
    queryKey: ['tasa-bcv'],
    queryFn: () => tasasApi.actual().then(r => r.data),
    retry: false,
  })

  const totalIngresos = resultado ? Object.values(resultado.ingresos).reduce((s, v) => s + v, 0) : 0
  const totalGastos = resultado ? (resultado.costo_ventas + Object.values(resultado.gastos_operativos).reduce((s, v) => s + v, 0)) : 0

  // Chart data — top ingresos y gastos
  const chartData = resultado ? [
    ...Object.entries(resultado.ingresos).map(([name, value]) => ({ name: name.substring(0, 18), value, type: 'Ingreso' })),
    ...Object.entries(resultado.gastos_operativos).slice(0, 4).map(([name, value]) => ({ name: name.substring(0, 18), value, type: 'Gasto' })),
  ] : []

  const accesosRapidos = [
    { to: '/diario', icon: 'ti-plus', label: 'Nuevo asiento', color: 'bg-brand-500 text-white' },
    { to: '/nomina', icon: 'ti-users', label: 'Calcular nómina', color: 'bg-blue-500 text-white' },
    { to: '/iva', icon: 'ti-receipt', label: 'Registrar factura', color: 'bg-amber-500 text-white' },
    { to: '/seniat', icon: 'ti-file-text', label: 'Exportar SENIAT', color: 'bg-purple-500 text-white' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-display text-surface-900">Dashboard</h1>
          <p className="text-sm text-surface-500 mt-0.5">
            {MESES[mes - 1]} {new Date().getFullYear()} · Boeuf Contable
          </p>
        </div>
        {tasa && (
          <div className="flex items-center gap-2 bg-brand-50 border border-brand-200 rounded-xl px-4 py-2">
            <i className="ti ti-currency-dollar text-brand-500" />
            <span className="font-mono font-semibold text-brand-700">{fmtNum(tasa.tasa_usd)}</span>
            <span className="text-brand-500 text-sm">Bs./USD</span>
            <span className="text-brand-400 text-xs ml-1">BCV</span>
          </div>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Ingresos del mes" value={fmtBs(totalIngresos)} sub="Ventas del período"
          icon="ti-trending-up" color="text-brand-600" />
        <MetricCard label="Gastos del mes" value={fmtBs(totalGastos)} sub="Costos y gastos operativos"
          icon="ti-trending-down" color="text-danger" />
        <MetricCard
          label="Utilidad neta"
          value={fmtBs(resultado?.utilidad_neta ?? 0)}
          sub={resultado?.utilidad_neta && resultado.utilidad_neta >= 0 ? 'Período rentable ✓' : 'Período con pérdidas'}
          icon="ti-report-money"
          color={resultado?.utilidad_neta && resultado.utilidad_neta >= 0 ? 'text-brand-600' : 'text-danger'}
        />
        <MetricCard label="Asientos registrados" value={String(asientos?.length ?? 0)} sub="Últimos registros"
          icon="ti-notebook" color="text-info" />
      </div>

      {/* Quick access */}
      <div>
        <h2 className="text-sm font-semibold text-surface-600 mb-3">Accesos rápidos</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {accesosRapidos.map(({ to, icon, label, color }) => (
            <Link
              key={to}
              to={to}
              className="card card-hover p-4 flex items-center gap-3 no-underline group"
            >
              <div className={`w-9 h-9 rounded-xl ${color} flex items-center justify-center flex-shrink-0`}>
                <i className={`ti ${icon} text-base`} />
              </div>
              <span className="text-sm font-medium text-surface-700 group-hover:text-surface-900">{label}</span>
              <i className="ti ti-chevron-right text-surface-300 text-sm ml-auto group-hover:translate-x-0.5 transition-transform" />
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-surface-700 mb-4">Ingresos vs Gastos — {MESES[mes - 1]}</h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barSize={28}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  formatter={(v: number) => fmtBs(v)}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '0.5px solid #e2e8f0' }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.type === 'Ingreso' ? '#1D9E75' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state h-[200px]">
              <i className="ti ti-chart-bar" />
              <p>Sin datos para el período</p>
            </div>
          )}
        </div>

        {/* Recent asientos */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-surface-700">Últimos asientos</h3>
            <Link to="/diario" className="text-xs text-brand-500 hover:text-brand-600">Ver todos →</Link>
          </div>
          <div className="space-y-2">
            {asientos?.length ? asientos.slice(0, 5).map(a => (
              <div key={a.id} className="flex items-center justify-between py-2 border-b border-surface-100 last:border-0">
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-mono font-medium text-surface-700">{a.numero_asiento}</div>
                  <div className="text-[11px] text-surface-400 truncate">{a.descripcion || 'Sin descripción'}</div>
                </div>
                <div className="text-right flex-shrink-0 ml-3">
                  <div className="text-xs font-mono text-surface-700">{fmtBs(a.total_debe)}</div>
                  <span className={`badge text-[9px] ${a.cuadra ? 'badge-green' : 'badge-red'}`}>
                    {a.cuadra ? '✓' : '✗'}
                  </span>
                </div>
              </div>
            )) : (
              <div className="empty-state py-8">
                <i className="ti ti-notebook" />
                <p>Sin asientos registrados</p>
              </div>
            )}
          </div>
          <Link to="/diario" className="btn-secondary w-full justify-center mt-3 text-xs">
            <i className="ti ti-plus" /> Nuevo asiento
          </Link>
        </div>
      </div>

      {/* Regulaciones info */}
      <div className="card p-4 bg-brand-50 border-brand-200">
        <div className="flex items-start gap-3">
          <i className="ti ti-shield-check text-brand-500 text-xl mt-0.5" />
          <div>
            <div className="text-sm font-semibold text-brand-800">Regulaciones venezolanas activas</div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {['IVA 16%', 'Ret. IVA 75% (SPE)', 'IGTF 3%', 'ISLR Progresivo 2025', 'SSO 4%/9%', 'FAOV 1%/2%', 'INCES 0.5%/2%', 'Pensiones 9%/9%', 'D.1808 Art.9'].map(r => (
                <span key={r} className="badge-green text-[10px]">{r}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
