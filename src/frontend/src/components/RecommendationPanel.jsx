import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'

/**
 * RecommendationPanel — shows up to 5 Duke menu items that fit the user's
 * remaining macro budget for today. Each card has a "Log This" button.
 */
export default function RecommendationPanel() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['recommendations'],
    queryFn:  () => api.get('/recommendations').then((r) => r.data),
  })

  const { mutate: logDirect, isPending } = useMutation({
    mutationFn: (item) =>
      api.post('/log', {
        food_name:          item.food_name,
        duke_item_name:     item.food_name,
        dining_location:    item.dining_location,
        calories:           item.calories,
        protein_g:          item.protein_g,
        carbs_g:            item.carbs_g,
        fat_g:              item.fat_g,
        serving_multiplier: 1.0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  return (
    <div className="card h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Recommended for You
        </h2>
        <button onClick={() => refetch()} className="text-xs text-duke-blue hover:underline">
          Refresh
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-6">
          <div className="w-6 h-6 border-4 border-duke-blue border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-500">Could not load recommendations.</p>
      )}

      {data?.recommendations?.length === 0 && (
        <p className="text-sm text-gray-400 py-4 text-center">
          You've hit your macro goals for today — great job!
        </p>
      )}

      <ul className="space-y-2">
        {data?.recommendations?.map((item, i) => (
          <li
            key={i}
            className="flex items-start justify-between gap-2 border border-gray-100 rounded-lg p-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{item.food_name}</p>
              <p className="text-xs text-gray-400">{item.dining_location}</p>
              <div className="flex gap-2 mt-1 text-xs text-gray-600">
                <span>{item.calories} kcal</span>
                <span>{item.protein_g}g P</span>
                <span>{item.carbs_g}g C</span>
                <span>{item.fat_g}g F</span>
              </div>
            </div>
            <button
              onClick={() => logDirect(item)}
              disabled={isPending}
              className="btn-primary text-xs px-3 py-1.5 whitespace-nowrap flex-shrink-0"
            >
              Log This
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
