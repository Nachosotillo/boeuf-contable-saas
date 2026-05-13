// InventarioPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { inventarioApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel, extractError } from '@/utils'
import { PageHeader, EmptyState, Spinner, Modal, Field } from '@/components/Common'
import type { MovimientoInvCreate } from '@/types'

export default function InventarioPage() {
  const [tipo, setTipo] = useState<'E' | 'S' | null>(null)
  const qc = useQueryClient()
  const { data: movs = [], isLoading } = useQuery({ queryKey: ['inventario'], queryFn: () => inventarioApi.listar().then(r => r.data) })
  const { data: saldo } = useQuery({ queryKey: ['inv-saldo'], queryFn: () => inventarioApi.saldo().then(r => r.data) })
  const { register, handleSubmit, reset } = useForm<MovimientoInvCreate>({ defaultValues: { unidad: 'kg', tipo: 'E' } })
  const crear = useMutation({ mutationFn: (d: MovimientoInvCreate) => inventarioApi.registrar({ ...d, tipo: tipo! }), onSuccess: () => { toast.success('Movimiento registrado ✓'); qc.invalidateQueries({ queryKey: ['inventario'] }); qc.invalidateQueries({ queryKey: ['inv-saldo'] }); setTipo(null); reset() }, onError: (e) => toast.error(extractError(e)) })
  const handleExport = () => exportarExcel((movs as any[]).map(m => ({ Fecha: m.fecha, Descripción: m.descripcion, Tipo: m.tipo === 'E' ? 'ENTRADA' : 'SALIDA', Unidad: m.unidad, Cantidad: m.cantidad, 'Costo Unit.': m.costo_unitario, 'Costo Total': m.costo_total, 'Saldo Uds.': m.saldo_unidades, 'Saldo Valor': m.saldo_valor })), 'Inventario_MP')
  return (
    <div>
      <PageHeader title="Inventario de Materia Prima" subtitle="Método PEPS (Primero en Entrar, Primero en Salir)"
        actions={<div className="flex gap-2"><button onClick={() => setTipo('E')} className="btn-primary btn-sm"><i className="ti ti-arrow-down" /> Entrada</button><button onClick={() => setTipo('S')} className="btn-secondary btn-sm"><i className="ti ti-arrow-up" /> Salida</button><button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button></div>} />
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="metric-card"><div className="metric-label">Saldo en unidades</div><div className="metric-value text-blue-600">{saldo?.saldo_unidades ?? 0}</div></div>
        <div className="metric-card"><div className="metric-label">Saldo en valor (Bs.)</div><div className="metric-value text-brand-600">{fmtBs(saldo?.saldo_valor ?? 0)}</div></div>
      </div>
      {isLoading ? <Spinner /> : <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Fecha</th><th>Descripción</th><th>Tipo</th><th>Unidad</th><th className="text-right">Cantidad</th><th className="text-right">Costo Unit.</th><th className="text-right">Costo Total</th><th className="text-right">Saldo Uds.</th><th className="text-right">Saldo Valor</th></tr></thead>
          <tbody>{(movs as any[]).length ? (movs as any[]).map((m: any) => (
            <tr key={m.id}><td className="font-mono text-xs">{fmtDate(m.fecha)}</td><td className="max-w-[180px] truncate">{m.descripcion}</td><td><span className={`badge ${m.tipo === 'E' ? 'badge-green' : 'badge-amber'}`}>{m.tipo === 'E' ? 'ENTRADA' : 'SALIDA'}</span></td><td className="text-surface-400">{m.unidad}</td><td className="text-right font-mono">{m.cantidad}</td><td className="text-right font-mono">{fmtBs(m.costo_unitario)}</td><td className="text-right font-mono">{fmtBs(m.costo_total)}</td><td className="text-right font-mono text-blue-600">{m.saldo_unidades}</td><td className="text-right font-mono font-semibold text-brand-600">{fmtBs(m.saldo_valor)}</td></tr>
          )) : <tr><td colSpan={9}><EmptyState icon="ti-package" message="Sin movimientos de inventario" /></td></tr>}</tbody>
        </table>
      </div>}
      <Modal open={tipo !== null} onClose={() => { setTipo(null); reset() }} title={tipo === 'E' ? 'Registrar entrada de MP' : 'Registrar salida a producción'}
        footer={<><button onClick={() => { setTipo(null); reset() }} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => crear.mutate(d))} disabled={crear.isPending} className="btn-primary">{crear.isPending ? 'Guardando…' : tipo === 'E' ? 'Registrar entrada' : 'Registrar salida'}</button></>}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Fecha"><input type="date" className="input" {...register('fecha', { required: true })} /></Field>
          <Field label="Unidad"><select className="input" {...register('unidad')}><option value="kg">kg</option><option value="lt">lt</option><option value="und">und</option><option value="g">g</option></select></Field>
          <Field label={tipo === 'E' ? 'Proveedor' : 'Destino (Orden de Producción)'}><input className="input" placeholder={tipo === 'E' ? 'Molinos del Sur, C.A.' : 'Orden 001 — Tequeños'} {...register('descripcion', { required: true })} /></Field>
          <div /><Field label="Cantidad"><input type="number" min="0" step="0.0001" className="input" {...register('cantidad', { required: true, min: 0 })} /></Field>
          <Field label="Costo unitario (Bs.)"><input type="number" min="0" step="0.0001" className="input" {...register('costo_unitario', { required: true, min: 0 })} /></Field>
        </div>
      </Modal>
    </div>
  )
}
