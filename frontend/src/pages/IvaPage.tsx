// IvaPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { ivaApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcelMultiHoja, extractError, mesActual } from '@/utils'
import { PageHeader, Spinner, EmptyState, Modal, Field, MesSelector } from '@/components/Common'
import type { LibroIvaCompraCreate, LibroIvaVentaCreate } from '@/types'

export default function IvaPage() {
  const [mes, setMes] = useState<number | undefined>(mesActual())
  const [modalType, setModalType] = useState<'compra' | 'venta' | null>(null)
  const qc = useQueryClient()

  const { data: compras = [], isLoading: lc } = useQuery({ queryKey: ['iva-compras', mes], queryFn: () => ivaApi.listarCompras(mes).then(r => r.data) })
  const { data: ventas = [], isLoading: lv } = useQuery({ queryKey: ['iva-ventas', mes], queryFn: () => ivaApi.listarVentas(mes).then(r => r.data) })
  const { data: liq } = useQuery({ queryKey: ['iva-liq', mes], queryFn: () => ivaApi.liquidacion(mes).then(r => r.data) })

  const { register: rC, handleSubmit: hC, reset: resetC, watch: wC } = useForm<LibroIvaCompraCreate>({ defaultValues: { alicuota_iva: 0.16, paga_en_divisas: false, cliente_es_spe: false } })
  const { register: rV, handleSubmit: hV, reset: resetV, watch: wV } = useForm<LibroIvaVentaCreate>({ defaultValues: { alicuota_iva: 0.16, cliente_es_spe: false } })

  const baseC = Number(wC('base_imponible')) || 0, ivaC = baseC * 0.16, retC = wC('cliente_es_spe') ? ivaC * 0.75 : 0
  const baseV = Number(wV('base_imponible')) || 0, ivaV = baseV * 0.16, retV = wV('cliente_es_spe') ? ivaV * 0.75 : 0

  const mutC = useMutation({ mutationFn: (d: LibroIvaCompraCreate) => ivaApi.registrarCompra(d), onSuccess: () => { toast.success('Compra IVA registrada ✓'); qc.invalidateQueries({ queryKey: ['iva-compras'] }); qc.invalidateQueries({ queryKey: ['iva-liq'] }); setModalType(null); resetC() }, onError: (e) => toast.error(extractError(e)) })
  const mutV = useMutation({ mutationFn: (d: LibroIvaVentaCreate) => ivaApi.registrarVenta(d), onSuccess: () => { toast.success('Venta IVA registrada ✓'); qc.invalidateQueries({ queryKey: ['iva-ventas'] }); qc.invalidateQueries({ queryKey: ['iva-liq'] }); setModalType(null); resetV() }, onError: (e) => toast.error(extractError(e)) })

  const handleExport = () => exportarExcelMultiHoja([
    { name: 'IVA Compras', data: compras.map(r => ({ Fecha: r.fecha, Factura: r.numero_factura, Proveedor: r.proveedor, RIF: r.rif_proveedor, Base: r.base_imponible, 'IVA CF': r.iva_credito_fiscal, 'Ret 75%': r.retencion_iva_75, 'IGTF': r.igtf_aplicado, Total: r.total_factura })) },
    { name: 'IVA Ventas', data: ventas.map(r => ({ Fecha: r.fecha, Factura: r.numero_factura, Cliente: r.cliente, RIF: r.rif_cliente, Base: r.base_imponible, 'IVA DF': r.iva_debito_fiscal, 'Ret. Rec.': r.retencion_iva_recibida, Total: r.total_factura })) },
  ], 'Libros_IVA')

  return (
    <div>
      <PageHeader title="Libros IVA" subtitle="Compras y ventas con liquidación automática"
        actions={<div className="flex gap-2">
          <button onClick={() => setModalType('compra')} className="btn-secondary btn-sm"><i className="ti ti-plus" /> Compra IVA</button>
          <button onClick={() => setModalType('venta')} className="btn-primary btn-sm"><i className="ti ti-plus" /> Venta IVA</button>
          <button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button>
          <MesSelector mes={mes} onChange={setMes} />
        </div>} />

      {/* Liquidación */}
      {liq && (
        <div className={`card p-4 mb-4 flex items-center justify-between ${liq.tipo === 'A_PAGAR' ? 'border-danger/30 bg-red-50' : 'border-brand-200 bg-brand-50'}`}>
          <div className="flex gap-6 text-sm">
            <span><span className="text-surface-500">(+) IVA Débito Fiscal: </span><span className="font-mono font-semibold text-surface-800">{fmtBs(liq.iva_debito_fiscal)}</span></span>
            <span><span className="text-surface-500">(−) IVA Crédito Fiscal: </span><span className="font-mono font-semibold text-surface-800">{fmtBs(liq.iva_credito_fiscal)}</span></span>
            <span><span className="text-surface-500">(−) Retenciones: </span><span className="font-mono font-semibold text-surface-800">{fmtBs(liq.retenciones_recibidas)}</span></span>
          </div>
          <div className={`text-lg font-bold font-display ${liq.tipo === 'A_PAGAR' ? 'text-danger' : 'text-brand-600'}`}>
            IVA {liq.tipo === 'A_PAGAR' ? 'A PAGAR' : 'A FAVOR'}: {fmtBs(liq.iva_neto)}
          </div>
        </div>
      )}

      <h3 className="text-sm font-semibold text-surface-700 mb-2">Libro de Compras</h3>
      <div className="table-wrap mb-4">{lc ? <Spinner /> : (
        <table className="data-table">
          <thead><tr><th>Fecha</th><th>Factura</th><th>Proveedor</th><th>RIF</th><th className="text-right">Base</th><th className="text-right">IVA CF</th><th className="text-right">Ret. 75%</th><th className="text-right">IGTF</th><th className="text-right">Total</th></tr></thead>
          <tbody>{compras.length ? compras.map(r => (
            <tr key={r.id}><td className="font-mono text-xs">{fmtDate(r.fecha)}</td><td className="font-mono text-xs">{r.numero_factura}</td><td>{r.proveedor}</td><td className="font-mono text-xs">{r.rif_proveedor}</td><td className="text-right font-mono">{fmtBs(r.base_imponible)}</td><td className="text-right font-mono text-brand-600">{fmtBs(r.iva_credito_fiscal)}</td><td className="text-right font-mono text-danger">{r.retencion_iva_75 > 0 ? fmtBs(r.retencion_iva_75) : '—'}</td><td className="text-right font-mono">{r.igtf_aplicado > 0 ? fmtBs(r.igtf_aplicado) : '—'}</td><td className="text-right font-mono font-semibold">{fmtBs(r.total_factura)}</td></tr>
          )) : <tr><td colSpan={9}><EmptyState icon="ti-receipt" message="Sin compras IVA" /></td></tr>}</tbody>
        </table>
      )}</div>

      <h3 className="text-sm font-semibold text-surface-700 mb-2">Libro de Ventas</h3>
      <div className="table-wrap">{lv ? <Spinner /> : (
        <table className="data-table">
          <thead><tr><th>Fecha</th><th>Factura</th><th>Cliente</th><th>RIF</th><th className="text-right">Base</th><th className="text-right">IVA DF</th><th className="text-right">Ret. Rec.</th><th className="text-right">Total</th><th>SPE</th></tr></thead>
          <tbody>{ventas.length ? ventas.map(r => (
            <tr key={r.id}><td className="font-mono text-xs">{fmtDate(r.fecha)}</td><td className="font-mono text-xs">{r.numero_factura}</td><td>{r.cliente}</td><td className="font-mono text-xs">{r.rif_cliente}</td><td className="text-right font-mono">{fmtBs(r.base_imponible)}</td><td className="text-right font-mono text-danger">{fmtBs(r.iva_debito_fiscal)}</td><td className="text-right font-mono">{r.retencion_iva_recibida > 0 ? fmtBs(r.retencion_iva_recibida) : '—'}</td><td className="text-right font-mono font-semibold">{fmtBs(r.total_factura)}</td><td>{r.cliente_es_spe ? <span className="badge badge-amber">SPE</span> : ''}</td></tr>
          )) : <tr><td colSpan={9}><EmptyState icon="ti-receipt-2" message="Sin ventas IVA" /></td></tr>}</tbody>
        </table>
      )}</div>

      {/* Modal Compra */}
      <Modal open={modalType === 'compra'} onClose={() => { setModalType(null); resetC() }} title="Registrar compra IVA"
        footer={<><button onClick={() => { setModalType(null); resetC() }} className="btn-secondary">Cancelar</button><button onClick={hC(d => mutC.mutate(d))} disabled={mutC.isPending} className="btn-primary">{mutC.isPending ? 'Guardando…' : 'Registrar compra'}</button></>}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Fecha"><input type="date" className="input" {...rC('fecha', { required: true })} /></Field>
            <Field label="N° Factura / Control"><input className="input" placeholder="F-0001 / C-0001" {...rC('numero_factura', { required: true })} /></Field>
            <Field label="Proveedor"><input className="input" placeholder="Razón social" {...rC('proveedor', { required: true })} /></Field>
            <Field label="RIF Proveedor"><input className="input" placeholder="J-00000000-0" {...rC('rif_proveedor', { required: true })} /></Field>
            <Field label="Base Imponible (Bs.)"><input type="number" min="0" step="0.01" className="input" {...rC('base_imponible', { required: true, min: 0 })} /></Field>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" className="rounded" {...rC('paga_en_divisas')} /> Pago en divisas (IGTF 3%)</label>
            <label className="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" className="rounded" {...rC('cliente_es_spe')} /> Soy SPE (Ret. IVA 75%)</label>
          </div>
          {baseC > 0 && (
            <div className="bg-surface-50 rounded-lg px-4 py-2.5 text-xs space-y-1">
              <div className="flex justify-between"><span>IVA Crédito Fiscal (16%):</span><span className="font-mono font-medium text-brand-600">{fmtBs(ivaC)}</span></div>
              {retC > 0 && <div className="flex justify-between"><span>Retención IVA 75%:</span><span className="font-mono text-danger">{fmtBs(retC)}</span></div>}
              <div className="flex justify-between font-semibold border-t border-surface-200 pt-1 mt-1"><span>Total Factura:</span><span className="font-mono">{fmtBs(baseC + ivaC)}</span></div>
            </div>
          )}
        </div>
      </Modal>

      {/* Modal Venta */}
      <Modal open={modalType === 'venta'} onClose={() => { setModalType(null); resetV() }} title="Registrar venta IVA"
        footer={<><button onClick={() => { setModalType(null); resetV() }} className="btn-secondary">Cancelar</button><button onClick={hV(d => mutV.mutate(d))} disabled={mutV.isPending} className="btn-primary">{mutV.isPending ? 'Guardando…' : 'Registrar venta'}</button></>}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Fecha"><input type="date" className="input" {...rV('fecha', { required: true })} /></Field>
            <Field label="N° Factura / Control"><input className="input" placeholder="F-0001 / C-0001" {...rV('numero_factura', { required: true })} /></Field>
            <Field label="Cliente"><input className="input" placeholder="Razón social" {...rV('cliente', { required: true })} /></Field>
            <Field label="RIF Cliente"><input className="input" placeholder="J-00000000-0" {...rV('rif_cliente', { required: true })} /></Field>
            <Field label="Base Imponible (Bs.)"><input type="number" min="0" step="0.01" className="input" {...rV('base_imponible', { required: true, min: 0 })} /></Field>
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" className="rounded" {...rV('cliente_es_spe')} /> Cliente es SPE (retiene 75% del IVA)</label>
          {baseV > 0 && (
            <div className="bg-surface-50 rounded-lg px-4 py-2.5 text-xs space-y-1">
              <div className="flex justify-between"><span>IVA Débito Fiscal (16%):</span><span className="font-mono font-medium text-danger">{fmtBs(ivaV)}</span></div>
              {retV > 0 && <div className="flex justify-between"><span>Retención recibida:</span><span className="font-mono">{fmtBs(retV)}</span></div>}
              <div className="flex justify-between font-semibold border-t border-surface-200 pt-1 mt-1"><span>Total Factura:</span><span className="font-mono">{fmtBs(baseV + ivaV)}</span></div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
