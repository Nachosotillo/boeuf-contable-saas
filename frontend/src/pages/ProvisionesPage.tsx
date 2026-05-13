// ProvisionesPage.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { nominaApi } from '@/services/api'
import { fmtBs, exportarExcel, extractError } from '@/utils'
import { PageHeader, ExportBar, EmptyState, Spinner } from '@/components/Common'
import type { EmpleadoOut } from '@/types'

function calcProv(emp: EmpleadoOut) {
  const sd = emp.salario_base / 30
  const pV = Math.round(sd * (15 / 12) * 100) / 100
  const pU = Math.round(sd * (30 / 12) * 100) / 100
  const pa = emp.anos_servicio >= 5 ? Math.round(sd * 30 * emp.anos_servicio / 5 * 100) / 100 : 0
  return { sd: Math.round(sd * 100) / 100, pV, pU, pa, tot: pV + pU + pa }
}

export default function ProvisionesPage() {
  const qc = useQueryClient()
  const { data: empleados = [], isLoading } = useQuery<EmpleadoOut[]>({ queryKey: ['empleados'], queryFn: () => nominaApi.listarEmpleados().then(r => r.data) })
  const genAsiento = useMutation({ mutationFn: () => import('@/services/api').then(m => m.api.post('/nomina/generar-provisiones')), onSuccess: () => { toast.success('Asiento provisiones generado ✓'); qc.invalidateQueries({ queryKey: ['asientos'] }) }, onError: (e) => toast.error(extractError(e)) })
  const provs = empleados.map(e => ({ ...e, ...calcProv(e) }))
  const totV = provs.reduce((s, p) => s + p.pV, 0)
  const totU = provs.reduce((s, p) => s + p.pU, 0)
  const totT = provs.reduce((s, p) => s + p.tot, 0)
  const handleExport = () => exportarExcel(provs.map(p => ({ Cédula: p.cedula, Nombre: p.nombre_completo, 'Sal. Mensual': p.salario_base, 'Sal. Diario': p.sd, 'Prov. Vacaciones': p.pV, 'Prov. Utilidades': p.pU, 'Prima Antigüedad': p.pa, 'Total Provisión': p.tot })), 'Provisiones_Sociales')
  return (
    <div>
      <PageHeader title="Provisiones Sociales" subtitle="Vacaciones, utilidades y antigüedad mensualizadas"
        actions={<div className="flex gap-2"><button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button></div>} />
      <div className="grid grid-cols-3 gap-4 mb-4">
        {[['Prov. Vacaciones/mes', totV, 'text-brand-600'], ['Prov. Utilidades/mes', totU, 'text-amber-600'], ['Total Provisión/mes', totT, 'text-blue-600']].map(([l, v, c]) => (
          <div key={l as string} className="metric-card"><div className="metric-label">{l}</div><div className={`metric-value ${c}`}>{fmtBs(v as number)}</div></div>
        ))}
      </div>
      {isLoading ? <Spinner /> : <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Cédula</th><th>Nombre</th><th className="text-right">Salario</th><th className="text-right">Sal. Diario</th><th className="text-right">Prov. Vacac.</th><th className="text-right">Prov. Util.</th><th className="text-right">Prima Ant.</th><th className="text-right">Total Prov.</th></tr></thead>
          <tbody>{provs.length ? provs.map(p => (
            <tr key={p.id}><td className="font-mono text-xs">{p.cedula}</td><td>{p.nombre_completo}</td><td className="text-right font-mono">{fmtBs(p.salario_base)}</td><td className="text-right font-mono text-xs">{fmtBs(p.sd)}</td><td className="text-right font-mono text-brand-600">{fmtBs(p.pV)}</td><td className="text-right font-mono text-amber-600">{fmtBs(p.pU)}</td><td className="text-right font-mono">{p.pa > 0 ? fmtBs(p.pa) : '—'}</td><td className="text-right font-mono font-semibold text-blue-600">{fmtBs(p.tot)}</td></tr>
          )) : <tr><td colSpan={8}><EmptyState icon="ti-piggy-bank" message="Sin empleados registrados" /></td></tr>}</tbody>
        </table>
        {provs.length > 0 && <div className="flex justify-end gap-4 px-4 py-3 bg-surface-50 border-t border-surface-200 text-sm"><span><span className="text-surface-500">Asiento sugerido: </span><span className="font-mono text-xs">DEBE 6.2.02 → HABER 2.1.16 + 2.1.15</span></span></div>}
      </div>}
    </div>
  )
}
