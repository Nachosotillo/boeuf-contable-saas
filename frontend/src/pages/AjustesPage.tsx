// AjustesPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ajustesApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel } from '@/utils'
import { PageHeader, ExportBar, EmptyState, Spinner } from '@/components/Common'
import AsientoModal from '@/components/Forms/AsientoModal'
import type { AjusteOut } from '@/types'

const TIPO_LABELS: Record<string, string> = { depr: 'Depreciación', prov: 'Provisión', difer: 'Diferimiento', otro: 'Otro' }
const TIPO_COLORS: Record<string, string> = { depr: 'badge-blue', prov: 'badge-amber', difer: 'badge-gray', otro: 'badge-gray' }

export default function AjustesPage() {
  const [open, setOpen] = useState(false)
  const { data: ajustes = [], isLoading } = useQuery<AjusteOut[]>({
    queryKey: ['ajustes'],
    queryFn: () => ajustesApi.listar().then(r => r.data),
  })
  const handleExport = () => exportarExcel(
    ajustes.map(a => ({ 'N° Ajuste': a.numero_ajuste, Fecha: a.fecha, Tipo: TIPO_LABELS[a.tipo], Descripción: a.descripcion, 'Total Debe': a.total_debe, 'Total Haber': a.total_haber })),
    'Ajustes'
  )
  return (
    <div>
      <PageHeader title="Ajustes" subtitle="Depreciaciones, provisiones y diferimientos del período"
        actions={<button onClick={() => setOpen(true)} className="btn-primary"><i className="ti ti-plus" /> Nuevo ajuste</button>} />
      <ExportBar onExcelExport={handleExport} count={ajustes.length} countLabel="ajustes" />
      {isLoading ? <Spinner /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>N°</th><th>Fecha</th><th>Tipo</th><th>Descripción</th><th className="text-right">Debe</th><th className="text-right">Haber</th><th>Estado</th></tr></thead>
            <tbody>
              {ajustes.length ? ajustes.map(a => (
                <tr key={a.id}>
                  <td className="font-mono font-medium">{a.numero_ajuste}</td>
                  <td className="font-mono text-xs">{fmtDate(a.fecha)}</td>
                  <td><span className={`badge ${TIPO_COLORS[a.tipo]}`}>{TIPO_LABELS[a.tipo]}</span></td>
                  <td>{a.descripcion || '—'}</td>
                  <td className="text-right font-mono">{fmtBs(a.total_debe)}</td>
                  <td className="text-right font-mono">{fmtBs(a.total_haber)}</td>
                  <td><span className="badge badge-green">✓ Cuadra</span></td>
                </tr>
              )) : <tr><td colSpan={7}><EmptyState icon="ti-adjustments" message="Sin ajustes registrados" action={<button onClick={() => setOpen(true)} className="btn-primary btn-sm">Nuevo ajuste</button>} /></td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <AsientoModal open={open} onClose={() => setOpen(false)} tipo="ajuste" />
    </div>
  )
}
