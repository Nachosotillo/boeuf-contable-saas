// ActivosPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { activosApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel, extractError } from '@/utils'
import { PageHeader, EmptyState, Spinner, Modal, Field } from '@/components/Common'
import type { ActivoFijoCreate } from '@/types'

export default function ActivosPage() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const { data: activos = [], isLoading } = useQuery({ queryKey: ['activos'], queryFn: () => activosApi.listar().then(r => r.data) })
  const { register, handleSubmit, reset } = useForm<ActivoFijoCreate>({ defaultValues: { vida_util_anos: 10 } })
  const crear = useMutation({ mutationFn: (d: ActivoFijoCreate) => activosApi.crear(d), onSuccess: () => { toast.success('Activo registrado ✓'); qc.invalidateQueries({ queryKey: ['activos'] }); setOpen(false); reset() }, onError: (e) => toast.error(extractError(e)) })
  const genDepr = useMutation({ mutationFn: () => activosApi.generarDepreciacion(), onSuccess: (r) => { toast.success(`${r.data.numero_asiento} — Depreciación generada ✓`); qc.invalidateQueries({ queryKey: ['activos'] }); qc.invalidateQueries({ queryKey: ['asientos'] }) }, onError: (e) => toast.error(extractError(e)) })
  const totOrig = (activos as any[]).reduce((s: number, a: any) => s + Number(a.costo_original), 0)
  const totNeto = (activos as any[]).reduce((s: number, a: any) => s + Number(a.valor_neto), 0)
  const handleExport = () => exportarExcel((activos as any[]).map((a: any) => ({ Código: a.codigo_activo, Descripción: a.descripcion, 'F. Compra': a.fecha_compra, 'Costo Orig.': a.costo_original, 'Vida Útil': a.vida_util_anos + ' años', 'Depr. Mensual': a.depreciacion_mensual, 'Depr. Acum.': a.depreciacion_acumulada, 'Valor Neto': a.valor_neto })), 'Activos_Fijos')
  return (
    <div>
      <PageHeader title="Activos Fijos" subtitle="Depreciación por línea recta automática"
        actions={<div className="flex gap-2"><button onClick={() => setOpen(true)} className="btn-primary btn-sm"><i className="ti ti-plus" /> Nuevo activo</button><button onClick={() => genDepr.mutate()} disabled={!(activos as any[]).length || genDepr.isPending} className="btn-secondary btn-sm">{genDepr.isPending ? <><i className="ti ti-loader-2 animate-spin" /> Generando…</> : <><i className="ti ti-calculator" /> Generar depr. mensual</>}</button><button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button></div>} />
      <div className="grid grid-cols-3 gap-4 mb-4">
        {[['Activos registrados', (activos as any[]).length, 'text-blue-600'], ['Costo original total', fmtBs(totOrig), 'text-surface-900'], ['Valor neto total', fmtBs(totNeto), 'text-brand-600']].map(([l, v, c]) => (
          <div key={l as string} className="metric-card"><div className="metric-label">{l}</div><div className={`metric-value ${c}`}>{v}</div></div>
        ))}
      </div>
      {isLoading ? <Spinner /> : <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Código</th><th>Descripción</th><th>F. Compra</th><th className="text-right">Costo Orig.</th><th className="text-right">Vida Útil</th><th className="text-right">Depr. Mensual</th><th className="text-right">Depr. Acum.</th><th className="text-right">Valor Neto</th></tr></thead>
          <tbody>{(activos as any[]).length ? (activos as any[]).map((a: any) => (
            <tr key={a.id}><td className="font-mono text-xs font-medium">{a.codigo_activo}</td><td>{a.descripcion}</td><td className="font-mono text-xs">{fmtDate(a.fecha_compra)}</td><td className="text-right font-mono">{fmtBs(a.costo_original)}</td><td className="text-right text-surface-500">{a.vida_util_anos} años</td><td className="text-right font-mono text-amber-600">{fmtBs(a.depreciacion_mensual)}</td><td className="text-right font-mono text-danger">{fmtBs(a.depreciacion_acumulada)}</td><td className="text-right font-mono font-semibold text-brand-600">{fmtBs(a.valor_neto)}</td></tr>
          )) : <tr><td colSpan={8}><EmptyState icon="ti-building-factory" message="Sin activos registrados" /></td></tr>}</tbody>
        </table>
      </div>}
      <Modal open={open} onClose={() => { setOpen(false); reset() }} title="Registrar activo fijo"
        footer={<><button onClick={() => { setOpen(false); reset() }} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => crear.mutate(d))} disabled={crear.isPending} className="btn-primary">{crear.isPending ? 'Guardando…' : 'Registrar activo'}</button></>}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Código activo"><input className="input" placeholder="AF-006" {...register('codigo_activo', { required: true })} /></Field>
          <Field label="Descripción"><input className="input" placeholder="Nombre del activo" {...register('descripcion', { required: true })} /></Field>
          <Field label="Fecha compra"><input type="date" className="input" {...register('fecha_compra', { required: true })} /></Field>
          <Field label="Costo original (Bs.)"><input type="number" min="0" step="0.01" className="input" {...register('costo_original', { required: true, min: 0 })} /></Field>
          <Field label="Vida útil (años)"><input type="number" min="1" className="input" {...register('vida_util_anos', { required: true, min: 1 })} /></Field>
          <Field label="Cuenta GL activo"><input className="input" placeholder="1.2.05" {...register('cuenta_activo_codigo')} /></Field>
        </div>
      </Modal>
    </div>
  )
}
