// ─── DiarioPage.tsx ─────────────────────────────────────────────────────────
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { asientosApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel, extractError } from '@/utils'
import { PageHeader, ExportBar, MesSelector, EmptyState, Spinner } from '@/components/Common'
import AsientoModal from '@/components/Forms/AsientoModal'
import type { AsientoOut } from '@/types'

export function DiarioPage() {
  const [open, setOpen] = useState(false)
  const [mes, setMes] = useState<number | undefined>()
  const [expanded, setExpanded] = useState<number | null>(null)
  const qc = useQueryClient()

  const { data: asientos = [], isLoading } = useQuery<AsientoOut[]>({
    queryKey: ['asientos', mes],
    queryFn: () => asientosApi.listar({ mes }).then(r => r.data),
  })

  const reversar = useMutation({
    mutationFn: (id: number) => asientosApi.reversar(id),
    onSuccess: () => { toast.success('Asiento reversado'); qc.invalidateQueries({ queryKey: ['asientos'] }) },
    onError: (err) => toast.error(extractError(err)),
  })

  const handleExport = () => exportarExcel(
    asientos.map(a => ({ 'N° Asiento': a.numero_asiento, Fecha: a.fecha, Descripción: a.descripcion, Referencia: a.referencia, 'Total Debe': a.total_debe, 'Total Haber': a.total_haber, Cuadra: a.cuadra ? 'Sí' : 'No' })),
    'Diario_General', 'Diario General'
  )

  return (
    <div>
      <PageHeader title="Diario General" subtitle="Registro de asientos contables"
        actions={<button onClick={() => setOpen(true)} className="btn-primary"><i className="ti ti-plus" /> Nuevo asiento</button>} />
      <ExportBar onExcelExport={handleExport}
        extraActions={<MesSelector mes={mes} onChange={setMes} />}
        count={asientos.length} countLabel="asientos" />
      {isLoading ? <Spinner /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr>
              <th>N°</th><th>Fecha</th><th>Descripción</th><th>Referencia</th>
              <th className="text-right">Total Debe</th><th className="text-right">Total Haber</th>
              <th>Estado</th><th></th>
            </tr></thead>
            <tbody>
              {asientos.length ? asientos.map(a => (
                <>
                  <tr key={a.id} onClick={() => setExpanded(expanded === a.id ? null : a.id)} className="cursor-pointer">
                    <td><span className="font-mono font-medium text-surface-900">{a.numero_asiento}</span></td>
                    <td className="font-mono text-xs">{fmtDate(a.fecha)}</td>
                    <td className="max-w-[200px] truncate">{a.descripcion || <span className="text-surface-400">—</span>}</td>
                    <td className="text-surface-400 text-xs">{a.referencia || '—'}</td>
                    <td className="text-right font-mono">{fmtBs(a.total_debe)}</td>
                    <td className="text-right font-mono">{fmtBs(a.total_haber)}</td>
                    <td><span className={`badge ${a.cuadra ? 'badge-green' : 'badge-red'}`}>{a.cuadra ? '✓ Cuadra' : '✗ Error'}</span></td>
                    <td>
                      <div className="flex gap-1">
                        <button className="btn-icon text-surface-400 hover:text-brand-500" onClick={e => { e.stopPropagation(); setExpanded(expanded === a.id ? null : a.id) }}><i className={`ti ${expanded === a.id ? 'ti-chevron-up' : 'ti-chevron-down'}`} /></button>
                        <button className="btn-icon text-surface-400 hover:text-danger" title="Reversar" onClick={e => { e.stopPropagation(); if (confirm('¿Reversar asiento?')) reversar.mutate(a.id) }}><i className="ti ti-rotate" /></button>
                      </div>
                    </td>
                  </tr>
                  {expanded === a.id && (
                    <tr key={`exp-${a.id}`} className="bg-surface-50">
                      <td colSpan={8} className="px-4 py-3">
                        <div className="text-xs font-semibold text-surface-500 mb-2">LÍNEAS DEL ASIENTO</div>
                        <table className="w-full text-xs">
                          <thead><tr className="text-surface-400"><th className="text-left pb-1">Código</th><th className="text-left pb-1">Cuenta</th><th className="text-right pb-1">Debe</th><th className="text-right pb-1">Haber</th></tr></thead>
                          <tbody>
                            {a.lineas.map(l => (
                              <tr key={l.id}>
                                <td className="font-mono py-0.5 pr-3">{l.cuenta_codigo}</td>
                                <td className="py-0.5 pr-3 text-surface-700">{l.cuenta_nombre}</td>
                                <td className="text-right font-mono py-0.5 pr-3">{l.debe > 0 ? fmtBs(l.debe) : ''}</td>
                                <td className="text-right font-mono py-0.5">{l.haber > 0 ? fmtBs(l.haber) : ''}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </>
              )) : (
                <tr><td colSpan={8}><EmptyState icon="ti-notebook" message="Sin asientos. Crea el primero." action={<button onClick={() => setOpen(true)} className="btn-primary btn-sm">Nuevo asiento</button>} /></td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <AsientoModal open={open} onClose={() => setOpen(false)} tipo="asiento" />
    </div>
  )
}

export default DiarioPage
