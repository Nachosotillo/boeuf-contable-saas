import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { inventarioApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel, extractError } from '@/utils'
import { PageHeader, EmptyState, Spinner, Modal, Field } from '@/components/Common'

export default function InventarioPage() {
  const [tab, setTab] = useState<'articulos' | 'movimientos'>('articulos')
  const [modalArticulo, setModalArticulo] = useState(false)
  const [modalMovimiento, setModalMovimiento] = useState<'E' | 'S' | null>(null)
  const [selectedArticulo, setSelectedArticulo] = useState<number | ''>('')
  
  const qc = useQueryClient()
  
  // Queries
  const { data: articulos = [], isLoading: loadingArt } = useQuery({ 
    queryKey: ['articulos'], 
    queryFn: () => inventarioApi.listarArticulos().then(r => r.data) 
  })
  
  const { data: movimientos = [], isLoading: loadingMovs } = useQuery({ 
    queryKey: ['movimientos', selectedArticulo], 
    queryFn: () => inventarioApi.listarMovimientos(selectedArticulo || undefined).then(r => r.data) 
  })
  
  const { data: saldo } = useQuery({ 
    queryKey: ['inv-saldo'], 
    queryFn: () => inventarioApi.saldo().then(r => r.data) 
  })

  // Forms
  const formArt = useForm({ defaultValues: { tipo: 'Materia Prima', unidad_medida: 'kg' } })
  const formMov = useForm({ defaultValues: { tipo: 'E', articulo_id: '' } })

  // Mutations
  const crearArticulo = useMutation({ 
    mutationFn: (d: any) => inventarioApi.crearArticulo(d), 
    onSuccess: () => { 
      toast.success('Artículo creado ✓')
      qc.invalidateQueries({ queryKey: ['articulos'] })
      setModalArticulo(false)
      formArt.reset() 
    }, 
    onError: (e) => toast.error(extractError(e)) 
  })

  const registrarMov = useMutation({ 
    mutationFn: (d: any) => inventarioApi.registrarMovimiento({ ...d, tipo: modalMovimiento! }), 
    onSuccess: () => { 
      toast.success('Movimiento registrado ✓')
      qc.invalidateQueries({ queryKey: ['movimientos'] })
      qc.invalidateQueries({ queryKey: ['articulos'] })
      qc.invalidateQueries({ queryKey: ['inv-saldo'] })
      setModalMovimiento(null)
      formMov.reset() 
    }, 
    onError: (e) => toast.error(extractError(e)) 
  })

  const handleExportMovs = () => {
    const data = (movimientos as any[]).map(m => ({
      Fecha: m.fecha,
      'Artículo ID': m.articulo_id,
      Lote: m.lote || '-',
      Vencimiento: m.fecha_vencimiento || '-',
      Descripción: m.descripcion,
      Tipo: m.tipo === 'E' ? 'ENTRADA' : 'SALIDA',
      Cantidad: m.cantidad,
      'Costo Unit.': m.costo_unitario,
      'Costo Total': m.costo_total,
      'Saldo Uds.': m.saldo_unidades,
      'Saldo Valor': m.saldo_valor
    }))
    exportarExcel(data, 'Movimientos_Inventario')
  }

  return (
    <div>
      <PageHeader 
        title="Gestión de Inventario" 
        subtitle="Control PEPS, lotes y vencimientos para alimentos congelados"
        actions={
          <div className="flex gap-2">
            {tab === 'articulos' && (
              <button onClick={() => setModalArticulo(true)} className="btn-primary btn-sm">
                <i className="ti ti-plus" /> Nuevo Artículo
              </button>
            )}
            {tab === 'movimientos' && (
              <>
                <button onClick={() => setModalMovimiento('E')} className="btn-primary btn-sm">
                  <i className="ti ti-arrow-down" /> Entrada
                </button>
                <button onClick={() => setModalMovimiento('S')} className="btn-secondary btn-sm">
                  <i className="ti ti-arrow-up" /> Salida
                </button>
                <button onClick={handleExportMovs} className="btn-secondary btn-sm">
                  <i className="ti ti-file-spreadsheet" /> Excel
                </button>
              </>
            )}
          </div>
        } 
      />

      {/* Métricas Generales */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="metric-card">
          <div className="metric-label">Total Artículos Registrados</div>
          <div className="metric-value text-blue-600">{saldo?.total_articulos ?? 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Unidades Totales en Stock</div>
          <div className="metric-value text-brand-600">{saldo?.saldo_unidades ?? 0}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-surface-200 mb-4">
        <button 
          className={`px-4 py-2 text-sm font-medium ${tab === 'articulos' ? 'text-brand-600 border-b-2 border-brand-600' : 'text-surface-500 hover:text-surface-700'}`}
          onClick={() => setTab('articulos')}
        >
          Maestro de Artículos
        </button>
        <button 
          className={`px-4 py-2 text-sm font-medium ${tab === 'movimientos' ? 'text-brand-600 border-b-2 border-brand-600' : 'text-surface-500 hover:text-surface-700'}`}
          onClick={() => setTab('movimientos')}
        >
          Movimientos (Kardex)
        </button>
      </div>

      {/* Tab Content: Artículos */}
      {tab === 'articulos' && (
        <>
          {loadingArt ? <Spinner /> : <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Descripción</th>
                  <th>Tipo</th>
                  <th>Unidad</th>
                  <th className="text-right">Stock Mínimo</th>
                  <th className="text-right">Stock Actual</th>
                  <th className="text-center">Estado</th>
                </tr>
              </thead>
              <tbody>
                {(articulos as any[]).length ? (articulos as any[]).map((a: any) => (
                  <tr key={a.id}>
                    <td className="font-mono text-xs">{a.codigo_sku}</td>
                    <td className="font-medium">{a.descripcion}</td>
                    <td>
                      <span className={`badge ${a.tipo === 'Materia Prima' ? 'badge-blue' : a.tipo.includes('Terminado') ? 'badge-green' : 'badge-amber'}`}>
                        {a.tipo}
                      </span>
                    </td>
                    <td className="text-surface-500">{a.unidad_medida}</td>
                    <td className="text-right font-mono text-surface-500">{a.stock_minimo}</td>
                    <td className={`text-right font-mono font-bold ${a.stock_actual <= a.stock_minimo ? 'text-red-600' : 'text-green-600'}`}>
                      {a.stock_actual}
                    </td>
                    <td className="text-center">
                      <span className={`badge ${a.activo ? 'badge-green' : 'badge-red'}`}>{a.activo ? 'Activo' : 'Inactivo'}</span>
                    </td>
                  </tr>
                )) : <tr><td colSpan={7}><EmptyState icon="ti-package" message="Sin artículos registrados" /></td></tr>}
              </tbody>
            </table>
          </div>}
        </>
      )}

      {/* Tab Content: Movimientos */}
      {tab === 'movimientos' && (
        <>
          <div className="mb-4 max-w-sm">
            <label className="block text-sm font-medium text-surface-700 mb-1">Filtrar por Artículo</label>
            <select 
              className="input" 
              value={selectedArticulo} 
              onChange={e => setSelectedArticulo(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">Todos los artículos</option>
              {(articulos as any[]).map(a => (
                <option key={a.id} value={a.id}>{a.codigo_sku} - {a.descripcion}</option>
              ))}
            </select>
          </div>
          
          {loadingMovs ? <Spinner /> : <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Artículo</th>
                  <th>Lote</th>
                  <th>Vence</th>
                  <th>Descripción</th>
                  <th>Tipo</th>
                  <th className="text-right">Cantidad</th>
                  <th className="text-right">Costo U.</th>
                  <th className="text-right">Saldo U.</th>
                </tr>
              </thead>
              <tbody>
                {(movimientos as any[]).length ? (movimientos as any[]).map((m: any) => {
                  const art = (articulos as any[]).find(a => a.id === m.articulo_id);
                  return (
                    <tr key={m.id}>
                      <td className="font-mono text-xs">{fmtDate(m.fecha)}</td>
                      <td className="max-w-[120px] truncate" title={art?.descripcion}>{art?.descripcion || `ID: ${m.articulo_id}`}</td>
                      <td className="font-mono text-xs text-surface-500">{m.lote || '-'}</td>
                      <td className={`font-mono text-xs ${m.fecha_vencimiento && new Date(m.fecha_vencimiento) < new Date() ? 'text-red-600 font-bold' : ''}`}>
                        {m.fecha_vencimiento ? fmtDate(m.fecha_vencimiento) : '-'}
                      </td>
                      <td className="max-w-[150px] truncate">{m.descripcion}</td>
                      <td><span className={`badge ${m.tipo === 'E' ? 'badge-green' : 'badge-amber'}`}>{m.tipo === 'E' ? 'ENTRADA' : 'SALIDA'}</span></td>
                      <td className="text-right font-mono">{m.cantidad}</td>
                      <td className="text-right font-mono">{fmtBs(m.costo_unitario)}</td>
                      <td className="text-right font-mono text-blue-600 font-semibold">{m.saldo_unidades}</td>
                    </tr>
                  )
                }) : <tr><td colSpan={9}><EmptyState icon="ti-list" message="Sin movimientos de inventario" /></td></tr>}
              </tbody>
            </table>
          </div>}
        </>
      )}

      {/* Modal Artículo */}
      <Modal open={modalArticulo} onClose={() => { setModalArticulo(false); formArt.reset() }} title="Nuevo Artículo de Inventario"
        footer={<>
          <button onClick={() => { setModalArticulo(false); formArt.reset() }} className="btn-secondary">Cancelar</button>
          <button onClick={formArt.handleSubmit(d => crearArticulo.mutate(d))} disabled={crearArticulo.isPending} className="btn-primary">
            {crearArticulo.isPending ? 'Guardando…' : 'Crear Artículo'}
          </button>
        </>}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Código / SKU"><input className="input" placeholder="MP-001" {...formArt.register('codigo_sku', { required: true })} /></Field>
          <Field label="Descripción"><input className="input" placeholder="Harina Todo Uso" {...formArt.register('descripcion', { required: true })} /></Field>
          <Field label="Tipo de Inventario">
            <select className="input" {...formArt.register('tipo', { required: true })}>
              <option value="Materia Prima">Materia Prima</option>
              <option value="Producto en Proceso">Producto en Proceso</option>
              <option value="Producto Terminado">Producto Terminado</option>
              <option value="Suministros">Suministros</option>
            </select>
          </Field>
          <Field label="Unidad de Medida">
            <select className="input" {...formArt.register('unidad_medida', { required: true })}>
              <option value="kg">Kilo (kg)</option>
              <option value="g">Gramo (g)</option>
              <option value="lt">Litro (lt)</option>
              <option value="und">Unidad (und)</option>
              <option value="caja">Caja</option>
            </select>
          </Field>
          <Field label="Stock Mínimo (Alerta)"><input type="number" min="0" step="0.0001" className="input" {...formArt.register('stock_minimo', { required: true, min: 0 })} /></Field>
        </div>
      </Modal>

      {/* Modal Movimiento */}
      <Modal open={modalMovimiento !== null} onClose={() => { setModalMovimiento(null); formMov.reset() }} title={modalMovimiento === 'E' ? 'Registrar Entrada' : 'Registrar Salida'}
        footer={<>
          <button onClick={() => { setModalMovimiento(null); formMov.reset() }} className="btn-secondary">Cancelar</button>
          <button onClick={formMov.handleSubmit(d => registrarMov.mutate(d))} disabled={registrarMov.isPending} className="btn-primary">
            {registrarMov.isPending ? 'Guardando…' : modalMovimiento === 'E' ? 'Registrar entrada' : 'Registrar salida'}
          </button>
        </>}>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Fecha"><input type="date" className="input" {...formMov.register('fecha', { required: true })} /></Field>
          <Field label="Artículo">
            <select className="input" {...formMov.register('articulo_id', { required: true })}>
              <option value="">Seleccione artículo...</option>
              {(articulos as any[]).map(a => (
                <option key={a.id} value={a.id}>{a.codigo_sku} - {a.descripcion}</option>
              ))}
            </select>
          </Field>
          <Field label={modalMovimiento === 'E' ? 'Proveedor / Origen' : 'Destino (Orden)'}>
            <input className="input" placeholder={modalMovimiento === 'E' ? 'Factura 123 - Proveedor XYZ' : 'Orden Tequeños'} {...formMov.register('descripcion', { required: true })} />
          </Field>
          <Field label="Lote (Opcional)">
            <input className="input" placeholder="LOTE-001" {...formMov.register('lote')} />
          </Field>
          <Field label="Fecha de Vencimiento">
            <input type="date" className="input" {...formMov.register('fecha_vencimiento')} />
          </Field>
          <div />
          <Field label="Cantidad"><input type="number" min="0" step="0.0001" className="input" {...formMov.register('cantidad', { required: true, min: 0 })} /></Field>
          <Field label="Costo unitario (Bs.)"><input type="number" min="0" step="0.0001" className="input" {...formMov.register('costo_unitario', { required: true, min: 0 })} /></Field>
        </div>
      </Modal>
    </div>
  )
}
