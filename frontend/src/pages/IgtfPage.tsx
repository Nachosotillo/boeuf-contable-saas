// IgtfPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { igtfApi, tasasApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel, extractError } from '@/utils'
import { PageHeader, ExportBar, EmptyState, Spinner, Modal, Field } from '@/components/Common'
import type { OperacionIgtfCreate } from '@/types'

export default function IgtfPage() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const { data: ops = [], isLoading } = useQuery({ queryKey: ['igtf'], queryFn: () => igtfApi.listar().then(r => r.data) })
  const { data: tasa } = useQuery({ queryKey: ['tasa-bcv'], queryFn: () => tasasApi.actual().then(r => r.data), retry: false })
  const { register, handleSubmit, reset, watch } = useForm<OperacionIgtfCreate>({ defaultValues: { moneda: 'USD', tasa_bcv: tasa?.tasa_usd ?? 0 } })
  const mtoDiv = watch('monto_divisas') || 0, tasaBcv = watch('tasa_bcv') || 0
  const equiv = mtoDiv * tasaBcv, igtfCalc = equiv * 0.03
  const crear = useMutation({ mutationFn: (d: OperacionIgtfCreate) => igtfApi.registrar(d), onSuccess: () => { toast.success('IGTF registrado ✓'); qc.invalidateQueries({ queryKey: ['igtf'] }); setOpen(false); reset() }, onError: (e) => toast.error(extractError(e)) })
  const totalIgtf = ops.reduce((s: number, r: any) => s + Number(r.igtf_3_pct), 0)
  const handleExport = () => exportarExcel(ops.map((r: any) => ({ Fecha: r.fecha, 'N° Op.': r.numero_operacion, Cliente: r.cliente_pagador, RIF: r.rif, Moneda: r.moneda, 'Tasa BCV': r.tasa_bcv, 'Monto Div.': r.monto_divisas, 'Equiv. Bs.': r.equivalente_bs, 'IGTF 3%': r.igtf_3_pct })), 'IGTF')
  return (
    <div>
      <PageHeader title="IGTF — Impuesto a las Grandes Transacciones Financieras" subtitle="Operaciones en divisas · Alícuota 3% · Ley IGTF 2022"
        actions={<button onClick={() => setOpen(true)} className="btn-primary btn-sm"><i className="ti ti-plus" /> Registrar operación</button>} />
      <ExportBar onExcelExport={handleExport} count={ops.length} countLabel="operaciones"
        extraActions={<div className="ml-auto flex items-center gap-2 text-sm"><span className="text-surface-500">Total IGTF a enterar:</span><span className="font-mono font-semibold text-danger">{fmtBs(totalIgtf)}</span></div>} />
      {isLoading ? <Spinner /> : <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Fecha</th><th>N° Op.</th><th>Cliente/Pagador</th><th>RIF</th><th>Moneda</th><th className="text-right">Tasa BCV</th><th className="text-right">Monto Div.</th><th className="text-right">Equiv. Bs.</th><th className="text-right">IGTF 3%</th></tr></thead>
          <tbody>{ops.length ? ops.map((r: any) => (
            <tr key={r.id}><td className="font-mono text-xs">{fmtDate(r.fecha)}</td><td className="font-mono text-xs">{r.numero_operacion}</td><td>{r.cliente_pagador}</td><td className="font-mono text-xs">{r.rif}</td><td><span className="badge badge-blue">{r.moneda}</span></td><td className="text-right font-mono">{r.tasa_bcv}</td><td className="text-right font-mono">{r.monto_divisas}</td><td className="text-right font-mono">{fmtBs(r.equivalente_bs)}</td><td className="text-right font-mono font-semibold text-danger">{fmtBs(r.igtf_3_pct)}</td></tr>
          )) : <tr><td colSpan={9}><EmptyState icon="ti-currency-dollar" message="Sin operaciones IGTF" /></td></tr>}</tbody>
        </table>
      </div>}
      <Modal open={open} onClose={() => { setOpen(false); reset() }} title="Registrar operación IGTF"
        footer={<><button onClick={() => { setOpen(false); reset() }} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => crear.mutate(d))} disabled={crear.isPending} className="btn-primary">{crear.isPending ? 'Guardando…' : 'Registrar'}</button></>}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Fecha"><input type="date" className="input" {...register('fecha', { required: true })} /></Field>
            <Field label="N° Operación"><input className="input" placeholder="OP-0001" {...register('numero_operacion', { required: true })} /></Field>
            <Field label="Cliente/Pagador"><input className="input" {...register('cliente_pagador', { required: true })} /></Field>
            <Field label="RIF"><input className="input" placeholder="J-00000000-0" {...register('rif', { required: true })} /></Field>
            <Field label="Moneda"><select className="input" {...register('moneda')}><option value="USD">USD</option><option value="EUR">EUR</option><option value="COP">COP</option></select></Field>
            <Field label="Tasa BCV (Bs./div.)"><input type="number" step="0.0001" className="input font-mono" defaultValue={tasa?.tasa_usd ?? ''} {...register('tasa_bcv', { required: true, min: 0 })} /></Field>
            <Field label="Monto en divisas"><input type="number" step="0.0001" min="0" className="input" {...register('monto_divisas', { required: true, min: 0 })} /></Field>
          </div>
          {mtoDiv > 0 && tasaBcv > 0 && (
            <div className="bg-surface-50 rounded-lg px-4 py-2.5 text-xs space-y-1">
              <div className="flex justify-between"><span>Equivalente Bs.:</span><span className="font-mono font-medium">{fmtBs(equiv)}</span></div>
              <div className="flex justify-between font-semibold text-danger"><span>IGTF 3%:</span><span className="font-mono">{fmtBs(igtfCalc)}</span></div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
