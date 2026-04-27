import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import MacroRing from '../components/MacroRing'
import FoodUploader from '../components/FoodUploader'
import RecommendationPanel from '../components/RecommendationPanel'

function LogTable({ entries, onDelete }) {
  if (!entries?.length) {
    return (
      <p className="text-sm text-gray-400 py-4 text-center">
        No meals logged today. Photograph a dish above to get started!
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 uppercase border-b">
            <th className="pb-2 pr-3">Item</th>
            <th className="pb-2 pr-3">Location</th>
            <th className="pb-2 pr-3 text-right">kcal</th>
            <th className="pb-2 pr-3 text-right">P(g)</th>
            <th className="pb-2 pr-3 text-right">C(g)</th>
            <th className="pb-2 pr-3 text-right">F(g)</th>
            <th className="pb-2 text-right">×</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {entries.map((e) => (
            <tr key={e.id} className="hover:bg-gray-50">
              <td className="py-2 pr-3 font-medium max-w-[160px] truncate">{e.duke_item_name}</td>
              <td className="py-2 pr-3 text-gray-400 text-xs">{e.dining_location}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{e.calories}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{e.protein_g}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{e.carbs_g}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{e.fat_g}</td>
              <td className="py-2 text-right">
                <button
                  onClick={() => onDelete(e.id)}
                  className="text-red-400 hover:text-red-600 transition-colors text-xs"
                  title="Delete entry"
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DashboardPage() {
  const queryClient = useQueryClient()

  const today = new Date().toISOString().split('T')[0]

  const { data, isLoading } = useQuery({
    queryKey: ['log', today],
    queryFn:  () => api.get(`/log?date=${today}`).then((r) => r.data),
    refetchInterval: 60_000, // auto-refresh every 60 s
  })

  const { mutate: deleteEntry } = useMutation({
    mutationFn: (id) => api.delete(`/log/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-duke-navy">Dashboard</h1>
        <span className="text-sm text-gray-400">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
        </span>
      </div>

      {/* Macro rings */}
      {isLoading ? (
        <div className="card flex justify-center py-8">
          <div className="w-8 h-8 border-4 border-duke-blue border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <MacroRing totals={data?.totals} goals={data?.goals} />
      )}

      {/* Upload + recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FoodUploader />
        <RecommendationPanel />
      </div>

      {/* Food log table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Today's Food Log
          </h2>
          {data?.totals && (
            <span className="text-xs text-gray-400">
              {data.entries.length} {data.entries.length === 1 ? 'entry' : 'entries'}
            </span>
          )}
        </div>

        <LogTable entries={data?.entries} onDelete={deleteEntry} />

        {/* Daily totals footer */}
        {data?.entries?.length > 0 && (
          <div className="mt-4 pt-3 border-t grid grid-cols-4 text-center text-xs font-medium text-gray-500">
            <div>
              <p className="text-base font-bold text-gray-800">{data.totals.calories}</p>
              <p>kcal</p>
            </div>
            <div>
              <p className="text-base font-bold text-gray-800">{data.totals.protein_g}g</p>
              <p>protein</p>
            </div>
            <div>
              <p className="text-base font-bold text-gray-800">{data.totals.carbs_g}g</p>
              <p>carbs</p>
            </div>
            <div>
              <p className="text-base font-bold text-gray-800">{data.totals.fat_g}g</p>
              <p>fat</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
