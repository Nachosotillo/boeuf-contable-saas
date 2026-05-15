// NominaPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { nominaApi } from '@/services/api'
import { fmtBs, exportarExcel, extractError } from '@/utils'
import { PageHeader, ExportBar, EmptyState, Spinner, Modal, Field } from '@/components/Common'
import type { EmpleadoOut, NominaCalculadaOut, EmpleadoCreate } from '@/types'

export default function NominaPage() {
  const [openEmp, setOpenEmp] = useState(false)
  const [lunes, setLunes] = useState(4)
  const qc = useQueryClient()

  const { data: empleados = [], isLoading: loadEmp } = useQuery<EmpleadoOut[]>({ queryKey: ['empleados'], queryFn: () => nominaApi.listarEmpleados().then(r => r.data) })
  const { data: nomina = [] } = useQuery<NominaCalculadaOut[]>({ queryKey: ['nomina', lunes], queryFn: () => nominaApi.calcular({ lunes }).then(r => r.data), enabled: empleados.length > 0 })

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<EmpleadoCreate>({ defaultValues: { salario_base: 3500, bono_alimentacion: 0, anos_servicio: 0, tipo: 'MOD', porcentaje_ari: 0 } })

  const salarioWatch = watch('salario_base')
  const ariWatch = watch('porcentaje_ari')
  const islrPreview = (Number(salarioWatch) || 0) * ((Number(ariWatch) || 0) / 100)

  const crearEmp = useMutation({
    mutationFn: (data: EmpleadoCreate) => nominaApi.crearEmpleado(data),
    onSuccess: () => { toast.success('Empleado agregado ✓'); qc.invalidateQueries({ queryKey: ['empleados'] }); qc.invalidateQueries({ queryKey: ['nomina'] }); setOpenEmp(false); reset() },
    onError: (err) => toast.error(extractError(err)),
  })

  const eliminarEmp = useMutation({
    mutationFn: (id: number) => nominaApi.eliminarEmpleado(id),
    onSuccess: () => { toast.success('Empleado eliminado ✓'); qc.invalidateQueries({ queryKey: ['empleados'] }); qc.invalidateQueries({ queryKey: ['nomina'] }) },
    onError: (err) => toast.error(extractError(err)),
  })

  const genAsiento = useMutation({
    mutationFn: () => nominaApi.generarAsiento(),
    onSuccess: (res) => { toast.success(`Asiento ${res.data.numero_asiento} generado ✓`); qc.invalidateQueries({ queryKey: ['asientos'] }) },
    onError: (err) => toast.error(extractError(err)),
  })

  const handleExport = () => nomina.length && exportarExcel(
    nomina.map(n => ({ Cédula: n.cedula, Nombre: n.nombre, Cargo: n.cargo, Salario: n.salario_base, ISLR: n.islr_deducido, 'SSO 4%': n.sso_empleado, 'Paro Forzoso 0.5%': n.rpe_empleado, 'FAOV 1%': n.faov_empleado, 'INCES 0.5%': n.inces_empleado, 'Pensión 9%': n.proteccion_pensiones_emp, 'Total Ded.': n.total_deducciones, 'Neto a Pagar': n.neto_a_pagar, 'Costo Empresa': n.costo_total_empresa })),
    'Nomina'
  )

  const totNeto = nomina.reduce((s, n) => s + (Number(n.neto_a_pagar) || 0), 0)
  const totCosto = nomina.reduce((s, n) => s + (Number(n.costo_total_empresa) || 0), 0)

  return (
    <div>
      <PageHeader title="Nómina y Retenciones Legales" subtitle="Cálculo automático con topes salariales y cargas sociales según LOTTT/IVSS"
        actions={
          <div className="flex gap-2">
            <div className="flex items-center gap-2 mr-4 bg-surface-50 px-3 py-1 rounded-lg border border-surface-200">
              <label className="text-xs font-medium text-surface-600">Lunes del mes:</label>
              <select value={lunes} onChange={e => setLunes(Number(e.target.value))} className="bg-transparent font-bold text-brand-600 outline-none">
                <option value={4}>4 Lunes</option>
                <option value={5}>5 Lunes</option>
              </select>
            </div>
            <button onClick={() => setOpenEmp(true)} className="btn-primary btn-sm"><i className="ti ti-plus" /> Agregar empleado</button>
            <button onClick={() => genAsiento.mutate()} disabled={!empleados.length || genAsiento.isPending} className="btn-secondary btn-sm">
              {genAsiento.isPending ? <><i className="ti ti-loader-2 animate-spin" /> Generando…</> : <><i className="ti ti-notebook" /> Generar asiento</>}
            </button>
          </div>
        } />

      {/* Leyenda tasas */}
      <div className="flex flex-wrap gap-2 mb-4">
        {[['SSO', '4%/10%'], ['RPE (Paro Forzoso)', '0.5%/2%'], ['FAOV', '1%/2%'], ['INCES', '0%/2%'], ['Pensiones', '0%/9%'], ['ISLR', '% ARI']].map(([k, v]) => (
          <span key={k} className="badge badge-gray text-[10px]">{k}: <strong>{v}</strong></span>
        ))}
      </div>

      <ExportBar onExcelExport={handleExport} count={empleados.length} countLabel="empleados" />

      {loadEmp ? <Spinner /> : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Cédula</th><th>Nombre</th><th>Cargo</th>
                  <th className="text-right">Salario</th><th className="text-right">ISLR</th>
                  <th className="text-right">SSO</th><th className="text-right">RPE</th><th className="text-right">FAOV</th>
                  <th className="text-right">INCES</th><th className="text-right">Pensión</th>
                  <th className="text-right">Total Ded.</th>
                  <th className="text-right" style={{ color: '#1D9E75' }}>Neto</th>
                  <th className="text-right">Costo Emp.</th>
                </tr>
              </thead>
              <tbody>
                {nomina.length ? nomina.map(n => (
                  <tr key={n.empleado_id} className="group">
                    <td className="font-mono text-xs">{n.cedula}</td>
                    <td className="font-medium">{n.nombre}</td>
                    <td className="text-surface-500 text-xs">{n.cargo || '—'}</td>
                    <td className="text-right font-mono text-sm">{fmtBs(n.salario_base)}</td>
                    <td className="text-right font-mono text-danger text-xs">{fmtBs(n.islr_deducido)}</td>
                    <td className="text-right font-mono text-xs">{fmtBs(n.sso_empleado)}</td>
                    <td className="text-right font-mono text-xs text-brand-600 font-medium">{fmtBs(n.rpe_empleado)}</td>
                    <td className="text-right font-mono text-xs">{fmtBs(n.faov_empleado)}</td>
                    <td className="text-right font-mono text-xs">{fmtBs(n.inces_empleado)}</td>
                    <td className="text-right font-mono text-xs">{fmtBs(n.proteccion_pensiones_emp)}</td>
                    <td className="text-right font-mono text-danger font-semibold">{fmtBs(n.total_deducciones)}</td>
                    <td className="text-right font-mono text-brand-600 font-bold">{fmtBs(n.neto_a_pagar)}</td>
                    <td className="text-right font-mono text-blue-600 text-xs">{fmtBs(n.costo_total_empresa)}</td>
                    <td className="text-right">
                      <button onClick={() => { if(confirm('¿Desactivar empleado?')) eliminarEmp.mutate(n.empleado_id) }} className="opacity-0 group-hover:opacity-100 p-1 text-danger hover:bg-danger/10 rounded transition-all" title="Eliminar">
                        <i className="ti ti-trash" />
                      </button>
                    </td>
                  </tr>
                )) : <tr><td colSpan={14}><EmptyState icon="ti-users" message="Sin empleados. Agrega el primero." action={<button onClick={() => setOpenEmp(true)} className="btn-primary btn-sm">Agregar empleado</button>} /></td></tr>}
              </tbody>
            </table>
          </div>
          {nomina.length > 0 && (
            <div className="flex gap-6 justify-end px-4 py-3 bg-surface-50 border-t border-surface-200 rounded-b-xl">
              <div className="text-sm"><span className="text-surface-500">Neto total a pagar: </span><span className="font-mono font-semibold text-brand-600">{fmtBs(totNeto)}</span></div>
              <div className="text-sm"><span className="text-surface-500">Costo total empresa: </span><span className="font-mono font-semibold text-blue-600">{fmtBs(totCosto)}</span></div>
            </div>
          )}
        </>
      )}

      {/* Modal nuevo empleado */}
      <Modal open={openEmp} onClose={() => { setOpenEmp(false); reset() }} title="Agregar empleado"
        footer={<><button onClick={() => { setOpenEmp(false); reset() }} className="btn-secondary">Cancelar</button><button onClick={handleSubmit(d => crearEmp.mutate(d))} disabled={crearEmp.isPending} className="btn-primary">{crearEmp.isPending ? 'Guardando…' : 'Guardar'}</button></>}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Cédula" required error={errors.cedula?.message}><input className="input" placeholder="V-12345678" {...register('cedula', { required: 'Requerido' })} /></Field>
            <Field label="Nombre completo" required error={errors.nombre_completo?.message}><input className="input" placeholder="Juan Pérez" {...register('nombre_completo', { required: 'Requerido' })} /></Field>
            <Field label="Cargo"><input className="input" placeholder="Operario de Producción" {...register('cargo')} /></Field>
            <Field label="Fecha de Ingreso" error={errors.fecha_inicio?.message}><input type="date" className="input" {...register('fecha_inicio')} /></Field>
            <Field label="Tipo"><select className="input" {...register('tipo')}><option value="MOD">MOD — Directo</option><option value="MOI">MOI — Indirecto</option></select></Field>
            <Field label="Salario base (Bs.)" required>
              <input type="number" min="0" step="0.01" className="input" {...register('salario_base', { required: true, min: 0, valueAsNumber: true })} />
            </Field>
            <Field label="Porcentaje ARI (%)" error={errors.porcentaje_ari?.message}>
              <div className="relative">
                <input type="number" min="0" max="100" step="0.01" className="input pr-8" placeholder="2.79" {...register('porcentaje_ari', { valueAsNumber: true, min: 0, max: 100 })} />
                <span className="absolute right-3 top-2 text-surface-400">%</span>
              </div>
              {islrPreview > 0 && <p className="text-xs text-surface-500 mt-1">ISLR a descontar: <strong className="text-danger">{fmtBs(islrPreview)}</strong></p>}
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  )
}
