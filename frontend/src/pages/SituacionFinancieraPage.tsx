// SituacionFinancieraPage.tsx
import { useQuery } from '@tanstack/react-query'
import { reportesApi } from '@/services/api'
import { fmtBs } from '@/utils'
import { PageHeader, Spinner } from '@/components/Common'
import type { SituacionFinanciera } from '@/types'

function Section({ title, items, total, color }: { title: string; items: Record<string, number>; total: number; color: string }) {
  return (
    <div>
      <div className={`px-4 py-2 rounded-t-lg text-xs font-semibold uppercase tracking-wide ${color}`}>{title}</div>
      <div className="table-wrap rounded-t-none">
        <table className="data-table">
          <tbody>
            {Object.entries(items).filter(([, v]) => v !== 0).map(([k, v]) => (
              <tr key={k}><td className="pl-6 text-surface-600">{k}</td><td className="text-right font-mono">{fmtBs(v)}</td></tr>
            ))}
            <tr className="bg-surface-50 font-semibold"><td>Total {title}</td><td className="text-right font-mono">{fmtBs(total)}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function SituacionFinancieraPage() {
  const { data: sf, isLoading } = useQuery<SituacionFinanciera>({
    queryKey: ['situacion-financiera'],
    queryFn: () => reportesApi.situacionFinanciera().then(r => r.data),
  })
  return (
    <div>
      <PageHeader title="Estado de Situación Financiera" subtitle="Balance general acumulado"
        actions={sf && <span className={`badge ${sf.ecuacion_cuadra ? 'badge-green' : 'badge-red'}`}>{sf.ecuacion_cuadra ? 'Ecuación cuadra ✓' : 'Ecuación no cuadra ✗'}</span>} />
      {isLoading ? <Spinner /> : sf && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="font-semibold text-surface-700">ACTIVOS</h3>
            <Section title="Activo Corriente" items={sf.activo_corriente} total={Object.values(sf.activo_corriente).reduce((s, v) => s + v, 0)} color="bg-brand-50 text-brand-700" />
            <Section title="Activo No Corriente" items={sf.activo_no_corriente} total={Object.values(sf.activo_no_corriente).filter(v => v > 0).reduce((s, v) => s + v, 0)} color="bg-blue-50 text-blue-700" />
            <div className="card p-4 flex justify-between items-center bg-brand-500">
              <span className="font-semibold text-white">TOTAL ACTIVOS</span>
              <span className="font-bold text-white font-display text-lg">{fmtBs(sf.total_activos)}</span>
            </div>
          </div>
          <div className="space-y-4">
            <h3 className="font-semibold text-surface-700">PASIVOS Y PATRIMONIO</h3>
            <Section title="Pasivo Corriente" items={sf.pasivo_corriente} total={sf.total_pasivos} color="bg-red-50 text-red-700" />
            <Section title="Patrimonio" items={sf.patrimonio} total={sf.total_patrimonio} color="bg-amber-50 text-amber-700" />
            <div className={`card p-4 flex justify-between items-center ${sf.ecuacion_cuadra ? 'bg-brand-500' : 'bg-danger'}`}>
              <span className="font-semibold text-white">TOTAL PASIVO + PATRIMONIO</span>
              <span className="font-bold text-white font-display text-lg">{fmtBs(sf.total_pasivos + sf.total_patrimonio)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
