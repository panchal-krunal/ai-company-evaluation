import { useMemo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CHART } from '@/lib/chartTheme'
import { fiscalYear, formatCr, formatPct, niceTicks } from '@/lib/format'
import type { Growth } from './api'

const MARGINS = [
  { key: 'gross_margin', label: 'Gross margin', color: CHART.series[0] },
  { key: 'ebitda_margin', label: 'EBITDA margin', color: CHART.series[1] },
  { key: 'net_margin', label: 'Net margin', color: CHART.series[2] },
] as const

const axisProps = {
  tick: { fill: CHART.mutedText, fontSize: 12 },
  tickLine: false,
  axisLine: { stroke: CHART.axis },
} as const

function StatTile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-md border border-slate-200 px-4 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
      {note && <p className="text-xs text-slate-500">{note}</p>}
    </div>
  )
}

export function GrowthView({ growth }: { growth: Growth }) {
  const rows = useMemo(
    () => growth.years.map((y) => ({ ...y, fy: fiscalYear(y.period_end) })),
    [growth.years],
  )
  const latest = rows.at(-1)
  const revenueTicks = niceTicks(Math.max(...rows.map((r) => r.revenue ?? 0)))
  const first = rows[0]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label={`Revenue ${latest?.fy ?? ''}`} value={formatCr(latest?.revenue)} />
        <StatTile
          label="Latest year growth"
          value={formatPct(latest?.revenue_growth, { signed: true })}
        />
        <StatTile label="3-year revenue CAGR" value={formatPct(growth.revenue_cagr_3y)} />
        <StatTile
          label={`${growth.full_period_years}-year revenue CAGR`}
          value={formatPct(growth.revenue_cagr_full)}
          note={first && latest ? `${first.fy} → ${latest.fy}` : undefined}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <figure>
          <figcaption className="mb-2 text-sm font-medium">Revenue (₹ Cr)</figcaption>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={rows} margin={{ top: 20, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="fy" {...axisProps} />
                <YAxis
                  {...axisProps}
                  width={56}
                  ticks={revenueTicks}
                  domain={[0, revenueTicks.at(-1) ?? 'auto']}
                  tickFormatter={(v: number) => v.toLocaleString('en-IN')}
                />
                <Tooltip
                  cursor={{ fill: '#f1f0ec' }}
                  formatter={(value) => [formatCr(Number(value)), 'Revenue']}
                />
                <Bar
                  isAnimationActive={false}
                  dataKey="revenue"
                  fill={CHART.series[0]}
                  maxBarSize={24}
                  radius={[4, 4, 0, 0]}
                >
                  <LabelList
                    dataKey="revenue"
                    position="top"
                    fill={CHART.secondaryText}
                    fontSize={11}
                    formatter={(value) =>
                      Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })
                    }
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </figure>

        <figure>
          <figcaption className="mb-2 text-sm font-medium">Margins (% of revenue)</figcaption>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={rows} margin={{ top: 20, right: 16, bottom: 0, left: 8 }}>
                <CartesianGrid vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="fy" {...axisProps} />
                <YAxis
                  {...axisProps}
                  width={48}
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                />
                <ReferenceLine y={0} stroke={CHART.axis} />
                <Tooltip formatter={(value, name) => [formatPct(Number(value)), name]} />
                <Legend
                  itemSorter={null}
                  iconType="plainline"
                  wrapperStyle={{ fontSize: 12, color: CHART.secondaryText }}
                />
                {MARGINS.map((m) => (
                  <Line
                    isAnimationActive={false}
                    key={m.key}
                    type="linear"
                    dataKey={m.key}
                    name={m.label}
                    stroke={m.color}
                    strokeWidth={2}
                    dot={{ r: 4, fill: m.color, stroke: '#ffffff', strokeWidth: 2 }}
                    activeDot={{ r: 5, stroke: '#ffffff', strokeWidth: 2 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </figure>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <caption className="sr-only">Revenue and margins by fiscal year</caption>
          <thead className="text-xs tracking-wide text-slate-500 uppercase">
            <tr className="border-b border-slate-200">
              <th className="py-2 pr-4 text-left font-medium">Year</th>
              <th className="py-2 pr-4 text-right font-medium">Revenue</th>
              <th className="py-2 pr-4 text-right font-medium">Growth</th>
              <th className="py-2 pr-4 text-right font-medium">Gross margin</th>
              <th className="py-2 pr-4 text-right font-medium">EBITDA margin</th>
              <th className="py-2 text-right font-medium">Net margin</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.period_end} className="border-b border-slate-100 last:border-0">
                <td className="py-2 pr-4">{r.fy}</td>
                <td className="py-2 pr-4 text-right">{formatCr(r.revenue)}</td>
                <td className="py-2 pr-4 text-right">
                  {formatPct(r.revenue_growth, { signed: true })}
                </td>
                <td className="py-2 pr-4 text-right">{formatPct(r.gross_margin)}</td>
                <td className="py-2 pr-4 text-right">{formatPct(r.ebitda_margin)}</td>
                <td className="py-2 text-right">{formatPct(r.net_margin)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
