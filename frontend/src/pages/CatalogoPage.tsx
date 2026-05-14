// CatalogoPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { catalogoApi } from '@/services/api'
import { exportarExcel, extractError } from '@/utils'
import { PageHeader, ExportBar, EmptyState, Spinner, Modal, Field } from '@/components/Common'
import type { CatalogoCuenta, CuentaCreate } from '@/types'

export default function CatalogoPage() {
  const [open, setOpen] = useState(false)
  const [buscar, setBuscar] = useState('')
  const [filtroTipo, setFiltroTipo] = useState('')
  const qc = useQueryClient()

  const { data: cuentas = [], isLoading } = useQuery<CatalogoCuenta[]>({
    queryKey: ['catalogo'],
    queryFn: () => catalogoApi.listar().then(r => r.data),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CuentaCreate>()

  const crear = useMutation({
    mutationFn: (data: CuentaCreate) => catalogoApi.crear(data),
    onSuccess: () => { toast.success('Cuenta agregada ✓'); qc.invalidateQueries({ queryKey: ['catalogo'] }); setOpen(false); reset() },
    onError: (err) => toast.error(extractError(err)),
  })

  const cuentasFiltradas = cuentas.filter(c => {
    const q = buscar.toLowerCase()
    const matchQ = !q || c.codigo.toLowerCase().includes(q) || c.nombre.toLowerCase().includes(q)
    const matchT = !filtroTipo || c.tipo === filtroTipo
    return matchQ && matchT && c.activa
  })

  const handleExport = () => exportarExcel(
    cuentas.map(c => ({ Código: c.codigo, Nombre: c.nombre, Tipo: c.tipo, Naturaleza: c.naturaleza, 'Estado Financiero': c.estado_financiero })),
    'Catálogo_Cuentas'
  )

  return (
    <div>
      <PageHeader title="Catálogo de Cuentas" subtitle={`${cuentas.length} cuentas en el plan contable`}
        actions={<button onClick={() => setOpen(true)} className="btn-primary"><i className="ti ti-plus" /> Agregar cuenta</button>} />
      <div className="flex gap-2 mb-4 flex-wrap">
        <input className="input input-sm flex-1 min-w-[200px]" placeholder="Buscar por código o nombre…" value={buscar} onChange={e => setBuscar(e.target.value)} />
        <select className="input input-sm w-36" value={filtroTipo} onChange={e => setFiltroTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          <option value="Cuenta">Cuentas</option>
          <option value="Grupo">Grupos</option>
          <option value="Subgrupo">Subgrupos</option>
        </select>
        <button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button>
      </div>
      {isLoading ? <Spinner /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Código</th><th>Nombre</th><th>Tipo</th><th>Naturaleza</th><th>Subcategoría</th><th>Estado Financiero</th></tr></thead>
            <tbody>
              {cuentasFiltradas.length ? cuentasFiltradas.map(c => (
                <tr key={c.id}>
                  <td className="font-mono text-xs font-medium">{c.codigo}</td>
                  <td>{c.nombre}</td>
                  <td><span className={`badge ${c.tipo === 'Cuenta' ? 'badge-blue' : c.tipo === 'Grupo' ? 'badge-amber' : 'badge-gray'}`}>{c.tipo}</span></td>
                  <td className="text-surface-500 text-xs">{c.naturaleza ?? '—'}</td>
                  <td className="text-surface-500 text-xs">{c.subcategoria ?? '—'}</td>
                  <td className="text-surface-400 text-xs">{c.estado_financiero ?? '—'}</td>
                </tr>
              )) : <tr><td colSpan={6}><EmptyState icon="ti-list" message="Sin resultados" /></td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={open} onClose={() => { setOpen(false); reset() }} title="Agregar cuenta al catálogo"
        footer={<><button onClick={() => { setOpen(false); reset() }} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => crear.mutate(d))} disabled={crear.isPending} className="btn-primary">{crear.isPending ? <><i className="ti ti-loader-2 animate-spin" /> Guardando…</> : 'Guardar cuenta'}</button></>}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Código" required error={errors.codigo?.message}>
              <input className="input" placeholder="Ej: 1.1.35" {...register('codigo', { required: 'Requerido' })} />
            </Field>
            <Field label="Nombre" required error={errors.nombre?.message}>
              <input className="input" placeholder="Nombre de la cuenta" {...register('nombre', { required: 'Requerido' })} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo"><select className="input" {...register('tipo')}><option value="Cuenta">Cuenta</option><option value="Grupo">Grupo</option><option value="Subgrupo">Subgrupo</option></select></Field>
            <Field label="Naturaleza"><select className="input" {...register('naturaleza')}><option value="Deudora">Deudora</option><option value="Acreedora">Acreedora</option></select></Field>
            <Field label="Estado Financiero"><select className="input" {...register('estado_financiero')}><option value="Situación Financiera">Situación Financiera</option><option value="Estado de Resultado">Estado de Resultado</option><option value="Ninguno">Ninguno</option></select></Field>
            <Field label="Subcategoría (Opcional)">
              <input className="input" placeholder="Ej: Activo Corriente" {...register('subcategoria')} />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  )
}
