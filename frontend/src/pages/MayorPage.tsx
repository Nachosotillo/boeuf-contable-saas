// MayorPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { reportesApi, catalogoApi } from '@/services/api'
import { fmtBs, fmtDate, exportarExcel } from '@/utils'
import { PageHeader, EmptyState, Spinner, MesSelector, TableFooter } from '@/components/Common'
import type { MayorGeneral, CatalogoCuenta } from '@/types'

export default function MayorPage() {
  const [codigo, setCodigo] = useState('')
  const [mes, setMes] = useState<number | undefined>()

  const { data: cuentas = [] } = useQuery<CatalogoCuenta[]>({ queryKey: ['catalogo'], queryFn: () => catalogoApi.listar().then(r => r.data) })
  const { data: mayor, isLoading } = useQuery<MayorGeneral>({
    queryKey: ['mayor', codigo, mes],
    queryFn: () => reportesApi.mayorGeneral(codigo, mes).then(r => r.data),
    enabled: !!codigo,
  })

  const handleExport = () => mayor && exportarExcel(
    mayor.lineas.map(l => ({ Fecha: l.fecha, 'N° Asiento': l.numero_asiento, Descripción: l.descripcion, Debe: l.debe, Haber: l.haber, 'Saldo Acumulado': l.saldo_acumulado })),
    `Mayor_${codigo}`
  )

  return (
    <div>
      <PageHeader title="Mayor General" subtitle="Movimientos por cuenta con saldo acumulado" />
      <div className="flex gap-2 mb-4 flex-wrap">
        <select className="input input-sm flex-1 min-w-[250px]" value={codigo} onChange={e => setCodigo(e.target.value)}>
          <option value="">Seleccionar cuenta…</option>
          {cuentas.filter(c => c.tipo === 'Cuenta').map(c => <option key={c.codigo} value={c.codigo}>{c.codigo} — {c.nombre}</option>)}
        </select>
        <MesSelector mes={mes} onChange={setMes} />
        {mayor && <button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button>}
      </div>
      {!codigo ? (
        <div className="card p-8"><EmptyState icon="ti-book" message="Selecciona una cuenta para ver sus movimientos" /></div>
      ) : isLoading ? <Spinner /> : mayor ? (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Fecha</th><th>N° Asiento</th><th>Descripción</th><th className="text-right">Debe</th><th className="text-right">Haber</th><th className="text-right">Saldo</th></tr></thead>
              <tbody>
                {mayor.lineas.length ? mayor.lineas.map((l, i) => (
                  <tr key={i}>
                    <td className="font-mono text-xs">{fmtDate(l.fecha)}</td>
                    <td className="font-mono text-xs font-medium">{l.numero_asiento}</td>
                    <td className="max-w-[220px] truncate">{l.descripcion || '—'}</td>
                    <td className="text-right font-mono">{l.debe > 0 ? fmtBs(l.debe) : ''}</td>
                    <td className="text-right font-mono">{l.haber > 0 ? fmtBs(l.haber) : ''}</td>
                    <td className={`text-right font-mono font-semibold ${l.saldo_acumulado >= 0 ? 'text-brand-600' : 'text-danger'}`}>{fmtBs(l.saldo_acumulado)}</td>
                  </tr>
                )) : <tr><td colSpan={6}><EmptyState icon="ti-book" message="Sin movimientos para esta cuenta" /></td></tr>}
              </tbody>
            </table>
          </div>
          <TableFooter cols={[{ label: 'Total Debe', value: fmtBs(mayor.total_debe), color: 'text-brand-600' }, { label: 'Total Haber', value: fmtBs(mayor.total_haber), color: 'text-danger' }, { label: 'Saldo Final', value: fmtBs(mayor.saldo_final), color: mayor.saldo_final >= 0 ? 'text-brand-600' : 'text-danger' }]} />
        </>
      ) : null}
    </div>
  )
}
