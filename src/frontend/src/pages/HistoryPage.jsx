import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import api from '../api/client'

const MACRO_COLORS = {
  calories:  '#3b82f6',
  protein_g: '#22c55e',
  carbs_g:   '#f97316',
  fat_g:     '#a855f7',
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { weekday: 'short', month: 'numeric', day: 'numeric' })
}

function getLast7Days() {
  const today = new Date()
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today)
    d.setDate(today.getDate() - (6 - i))
    return d.toISOString().split('T')[0]
  })
}

export default function HistoryPage() {
  const days = getLast7Days()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['history'],
    queryFn: async () => {
      const results = await Promise.all(
        days.map((date) =>
          api.get(`/log?date=${date}`).then((r) => ({
            date,
            label:     formatDate(date),
            calories:  r.data.totals.calories,
            protein_g: r.data.totals.protein_g,
            carbs_g:   r.data.totals.carbs_g,
            fat_g:     r.data.totals.fat_g,
            goals:     r.data.goals,
          })),
        ),
      )
      return results
    },
    staleTime: 60_000,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-duke-navy">7-Day History</h1>

      {isLoading && (
        <div className="card flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-duke-blue border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {isError && (
        <div className="card">
          <p className="text-red-500 text-sm">Failed to load history.</p>
        </div>
      )}

      {data && (
        <>
          {/* Calories chart */}
          <div className="card">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Calories (kcal)
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(v) => [`${Math.round(v)} kcal`, 'Consumed']}
                  contentStyle={{ fontSize: 12 }}
                />
                <Bar dataKey="calories" fill={MACRO_COLORS.calories} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Macros chart */}
          <div className="card">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Macros (g)
            </h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="protein_g" name="Protein (g)" fill={MACRO_COLORS.protein_g} radius={[3, 3, 0, 0]} />
                <Bar dataKey="carbs_g"   name="Carbs (g)"   fill={MACRO_COLORS.carbs_g}   radius={[3, 3, 0, 0]} />
                <Bar dataKey="fat_g"     name="Fat (g)"     fill={MACRO_COLORS.fat_g}     radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Summary table */}
          <div className="card overflow-x-auto">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Daily Summary
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 uppercase border-b">
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 pr-4 text-right">Calories</th>
                  <th className="pb-2 pr-4 text-right">Protein (g)</th>
                  <th className="pb-2 pr-4 text-right">Carbs (g)</th>
                  <th className="pb-2 text-right">Fat (g)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.map((d) => (
                  <tr key={d.date} className="hover:bg-gray-50">
                    <td className="py-2 pr-4 font-medium">{d.label}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{Math.round(d.calories)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{Math.round(d.protein_g)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{Math.round(d.carbs_g)}</td>
                    <td className="py-2 text-right tabular-nums">{Math.round(d.fat_g)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
