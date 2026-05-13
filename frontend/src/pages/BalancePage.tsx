// BalancePage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { reportesApi } from '@/services/api'
import { fmtBs, exportarExcel } from '@/utils'
import { PageHeader, ExportBar, MesSelector, Spinner, TableFooter } from '@/components/Common'
import type { BalanceComprobacion } from '@/types'

export default function BalancePage() {
  const [mes, setMes] = useState<number | undefined>()
  const { data: balance, isLoading } = useQuery<BalanceComprobacion>({
    queryKey: ['balance', mes],
    queryFn: () => reportesApi.balanceComprobacion(mes).then(r => r.data),
  })
  const handleExport = () => balance && exportarExcel(
    balance.lineas.map(l => ({ Código: l.codigo, Nombre: l.nombre, Debe: l.debe, Haber: l.haber })),
    'Balance_Comprobacion'
  )
  return (
    <div>
      <PageHeader title="Balance de Comprobación" subtitle="Saldos acumulados del período"
        actions={balance && <span className={`badge ${balance.cuadra ? 'badge-green' : 'badge-red'}`}>{balance.cuadra ? '✓ Cuadra' : '✗ No cuadra'}</span>} />
      <ExportBar onExcelExport={handleExport}
        extraActions={<MesSelector mes={mes} onChange={setMes} />}
        count={balance?.lineas.length} />
      {isLoading ? <Spinner /> : balance && (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Código</th><th>Cuenta</th><th className="text-right">Debe (Bs.)</th><th className="text-right">Haber (Bs.)</th></tr></thead>
              <tbody>
                {balance.lineas.map(l => (
                  <tr key={l.codigo}>
                    <td className="font-mono text-xs">{l.codigo}</td>
                    <td>{l.nombre}</td>
                    <td className="text-right font-mono">{fmtBs(l.debe)}</td>
                    <td className="text-right font-mono">{fmtBs(l.haber)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <TableFooter cols={[
            { label: 'Total Debe', value: fmtBs(balance.total_debe), color: balance.cuadra ? 'text-brand-600' : 'text-danger' },
            { label: 'Total Haber', value: fmtBs(balance.total_haber), color: balance.cuadra ? 'text-brand-600' : 'text-danger' },
          ]} />
        </>
      )}
    </div>
  )
}
