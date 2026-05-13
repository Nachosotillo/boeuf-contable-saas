// EstadoResultadoPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { reportesApi } from '@/services/api'
import { fmtBs, exportarExcel, MESES, mesActual } from '@/utils'
import { PageHeader, MesSelector, Spinner } from '@/components/Common'
import type { EstadoResultado } from '@/types'

export default function EstadoResultadoPage() {
  const [mes, setMes] = useState<number | undefined>(mesActual())
  const { data: er, isLoading } = useQuery<EstadoResultado>({
    queryKey: ['estado-resultado', mes],
    queryFn: () => reportesApi.estadoResultado(mes).then(r => r.data),
  })
  const totalIngresos = er ? Object.values(er.ingresos).reduce((s, v) => s + v, 0) : 0
  const totalGastos = er ? Object.values(er.gastos_operativos).reduce((s, v) => s + v, 0) : 0

  const handleExport = () => er && exportarExcel([
    { Concepto: 'INGRESOS', Monto: '' },
    ...Object.entries(er.ingresos).map(([k, v]) => ({ Concepto: k, Monto: v })),
    { Concepto: 'Total Ingresos', Monto: totalIngresos },
    { Concepto: 'Costo de Ventas', Monto: -er.costo_ventas },
    ...Object.entries(er.gastos_operativos).map(([k, v]) => ({ Concepto: k, Monto: -v })),
    { Concepto: 'UTILIDAD NETA', Monto: er.utilidad_neta },
  ], 'Estado_Resultado')

  return (
    <div>
      <PageHeader title="Estado de Resultados"
        subtitle={mes ? MESES[mes - 1] : 'Acumulado'}
        actions={<div className="flex gap-2"><MesSelector mes={mes} onChange={setMes} />{er && <button onClick={handleExport} className="btn-secondary btn-sm"><i className="ti ti-file-spreadsheet" /> Excel</button>}</div>} />
      {isLoading ? <Spinner /> : er && (
        <div className="max-w-2xl">
          <div className="card overflow-hidden">
            {/* Ingresos */}
            <div className="px-5 py-3 bg-brand-50 border-b border-brand-100">
              <div className="text-xs font-semibold text-brand-700 uppercase tracking-wide">Ingresos Operacionales</div>
            </div>
            <table className="data-table">
              <tbody>
                {Object.entries(er.ingresos).map(([k, v]) => (
                  <tr key={k}><td className="pl-6">{k}</td><td className="text-right font-mono text-brand-600">{fmtBs(v)}</td></tr>
                ))}
                <tr className="bg-surface-50 font-semibold"><td>Total Ingresos</td><td className="text-right font-mono text-brand-700">{fmtBs(totalIngresos)}</td></tr>
              </tbody>
            </table>
            {/* Costos */}
            <div className="px-5 py-3 bg-surface-50 border-y border-surface-200">
              <div className="text-xs font-semibold text-surface-600 uppercase tracking-wide">Costos y Gastos</div>
            </div>
            <table className="data-table">
              <tbody>
                <tr><td className="pl-6">Costo de Ventas</td><td className="text-right font-mono text-danger">({fmtBs(er.costo_ventas)})</td></tr>
                {Object.entries(er.gastos_operativos).map(([k, v]) => (
                  <tr key={k}><td className="pl-6">{k}</td><td className="text-right font-mono text-danger">({fmtBs(v)})</td></tr>
                ))}
                <tr className="bg-surface-50 font-semibold"><td>Total Gastos</td><td className="text-right font-mono text-danger">({fmtBs(er.costo_ventas + totalGastos)})</td></tr>
              </tbody>
            </table>
            {/* Utilidad */}
            <div className={`px-5 py-4 flex justify-between items-center ${er.utilidad_neta >= 0 ? 'bg-brand-50' : 'bg-red-50'}`}>
              <span className="font-semibold text-surface-800">Utilidad / (Pérdida) Neta</span>
              <span className={`text-xl font-bold font-display ${er.utilidad_neta >= 0 ? 'text-brand-600' : 'text-danger'}`}>
                {er.utilidad_neta < 0 && '('}{fmtBs(Math.abs(er.utilidad_neta))}{er.utilidad_neta < 0 && ')'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
