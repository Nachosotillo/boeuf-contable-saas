// RetencionesPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { retencionesApi } from '@/services/api'
import { fmtBs, fmtPct, fmtDate, exportarExcel, extractError } from '@/utils'
import { PageHeader, ExportBar, EmptyState, Spinner, Modal, Field, MesSelector } from '@/components/Common'
import type { RetencionIslrCreate } from '@/types'

const CONCEPTOS: Record<string, number> = {
  'Honorarios Profesionales (PJ)': 0.03, 'Honorarios Profesionales (PN)': 0.03,
  'Arrendamiento Inmuebles': 0.05, 'Arrendamiento Muebles': 0.03,
  'Servicios — Contratistas PJ': 0.02, 'Publicidad y Propaganda': 0.03,
  'Comisiones a PN': 0.03, 'Intereses a PN': 0.03,
}

export default function RetencionesPage() {
  const [open, setOpen] = useState(false)
  const [mes, setMes] = useState<number | undefined>()
  const qc = useQueryClient()
  const { data: rets = [], isLoading } = useQuery({ queryKey: ['retenciones', mes], queryFn: () => retencionesApi.listar(mes).then(r => r.data) })
  const { register, handleSubmit, reset, watch } = useForm<RetencionIslrCreate>()
  const concepto = watch('concepto'), bruto = Number(watch('monto_bruto')) || 0
  const tasa = CONCEPTOS[concepto] ?? 0, retenido = bruto * tasa, neto = bruto - retenido
  const crear = useMutation({ mutationFn: (d: RetencionIslrCreate) => retencionesApi.crear(d), onSuccess: () => { toast.success('Retención ISLR registrada ✓'); qc.invalidateQueries({ queryKey: ['retenciones'] }); setOpen(false); reset() }, onError: (e) => toast.error(extractError(e)) })
  const totalRet = (rets as any[]).reduce((s: number, r: any) => s + Number(r.monto_retenido), 0)
  const handleExport = () => exportarExcel((rets as any[]).map(r => ({ Fecha: r.fecha_pago, Factura: r.numero_factura, Proveedor: r.beneficiario_nombre, RIF: r.beneficiario_rif, Concepto: r.concepto, '%': r.tasa_retencion * 100 + '%', Bruto: r.monto_bruto, Retenido: r.monto_retenido, Neto: r.monto_neto_pagado })), 'Retenciones_ISLR')
  return (
    <div>
      <PageHeader title="Retenciones ISLR" subtitle="Decreto 1808 — Agente de retención"
        actions={<button onClick={() => setOpen(true)} className="btn-primary btn-sm"><i className="ti ti-plus" /> Nueva retención</button>} />
      <ExportBar onExcelExport={handleExport} extraActions={<MesSelector mes={mes} onChange={setMes} />}
        count={(rets as any[]).length} countLabel="retenciones" />
      {isLoading ? <Spinner /> : <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Fecha</th><th>Factura</th><th>Proveedor</th><th>RIF</th><th>Concepto (D.1808)</th><th className="text-right">%</th><th className="text-right">Bruto</th><th className="text-right">Retenido</th><th className="text-right">Neto Pagado</th></tr></thead>
          <tbody>{(rets as any[]).length ? (rets as any[]).map((r: any) => (
            <tr key={r.id}><td className="font-mono text-xs">{fmtDate(r.fecha_pago)}</td><td className="font-mono text-xs">{r.numero_factura || '—'}</td><td>{r.beneficiario_nombre}</td><td className="font-mono text-xs">{r.beneficiario_rif}</td><td className="text-xs text-surface-500">{r.concepto}</td><td className="text-right font-mono">{fmtPct(r.tasa_retencion)}</td><td className="text-right font-mono">{fmtBs(r.monto_bruto)}</td><td className="text-right font-mono text-danger font-semibold">{fmtBs(r.monto_retenido)}</td><td className="text-right font-mono text-brand-600">{fmtBs(r.monto_neto_pagado)}</td></tr>
          )) : <tr><td colSpan={9}><EmptyState icon="ti-file-invoice" message="Sin retenciones ISLR registradas" /></td></tr>}</tbody>
        </table>
        {(rets as any[]).length > 0 && <div className="flex justify-end gap-6 px-4 py-3 bg-surface-50 border-t border-surface-200"><span className="text-sm"><span className="text-surface-500">Total retenido: </span><span className="font-mono font-semibold text-danger">{fmtBs(totalRet)}</span></span></div>}
      </div>}
      <Modal open={open} onClose={() => { setOpen(false); reset() }} title="Nueva retención ISLR — Decreto 1808"
        footer={<><button onClick={() => { setOpen(false); reset() }} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => crear.mutate(d))} disabled={crear.isPending} className="btn-primary">{crear.isPending ? 'Guardando…' : 'Registrar retención'}</button></>}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Fecha pago"><input type="date" className="input" {...register('fecha_pago', { required: true })} /></Field>
            <Field label="N° Factura"><input className="input" placeholder="FAC-0001" {...register('numero_factura')} /></Field>
            <Field label="Proveedor/Beneficiario"><input className="input" {...register('beneficiario_nombre', { required: true })} /></Field>
            <Field label="RIF Beneficiario"><input className="input" placeholder="J-00000000-0" {...register('beneficiario_rif', { required: true })} /></Field>
            <Field label="Concepto — Art. 9 Decreto 1808">
              <select className="input" {...register('concepto', { required: true })}><option value="">Seleccionar concepto…</option>{Object.keys(CONCEPTOS).map(c => <option key={c} value={c}>{c}</option>)}</select>
            </Field>
            <Field label="Monto bruto (Bs.)"><input type="number" min="0" step="0.01" className="input" {...register('monto_bruto', { required: true, min: 0 })} /></Field>
          </div>
          {bruto > 0 && tasa > 0 && (
            <div className="bg-surface-50 rounded-lg px-4 py-2.5 text-xs space-y-1">
              <div className="flex justify-between"><span>Tasa retención:</span><span className="font-mono font-semibold">{fmtPct(tasa)}</span></div>
              <div className="flex justify-between text-danger"><span>Monto retenido:</span><span className="font-mono font-semibold">{fmtBs(retenido)}</span></div>
              <div className="flex justify-between text-brand-600 font-semibold border-t border-surface-200 pt-1 mt-1"><span>Neto a pagar:</span><span className="font-mono">{fmtBs(neto)}</span></div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
