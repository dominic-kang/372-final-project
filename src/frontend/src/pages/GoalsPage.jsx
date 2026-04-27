import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import api from '../api/client'

const FIELDS = [
  { key: 'calorie_goal', label: 'Daily Calories', unit: 'kcal', min: 500,  max: 6000 },
  { key: 'protein_goal', label: 'Protein',         unit: 'g',   min: 10,   max: 500  },
  { key: 'carbs_goal',   label: 'Carbohydrates',   unit: 'g',   min: 10,   max: 1000 },
  { key: 'fat_goal',     label: 'Fat',             unit: 'g',   min: 5,    max: 300  },
]

export default function GoalsPage() {
  const queryClient = useQueryClient()

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn:  () => api.get('/profile').then((r) => r.data),
  })

  const [form, setForm] = useState({
    calorie_goal: 2200,
    protein_goal: 140,
    carbs_goal:   250,
    fat_goal:     70,
  })
  const [saved, setSaved] = useState(false)

  // Populate form once profile loads
  useEffect(() => {
    if (profile) {
      setForm({
        calorie_goal: profile.calorie_goal,
        protein_goal: profile.protein_goal,
        carbs_goal:   profile.carbs_goal,
        fat_goal:     profile.fat_goal,
      })
    }
  }, [profile])

  const { mutate: saveGoals, isPending, error } = useMutation({
    mutationFn: () => api.put('/profile/goals', form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      queryClient.invalidateQueries({ queryKey: ['log'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    },
  })

  function handleChange(key, val) {
    setForm((prev) => ({ ...prev, [key]: parseInt(val, 10) || 0 }))
    setSaved(false)
  }

  if (isLoading) return <p className="text-gray-500">Loading…</p>

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold text-duke-navy mb-1">Daily Goals</h1>
      <p className="text-sm text-gray-500 mb-6">
        Set your macro targets. These are used to calculate progress rings and recommendations.
      </p>

      <div className="card space-y-5">
        {FIELDS.map(({ key, label, unit, min, max }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}
              <span className="text-gray-400 font-normal ml-1">({unit})</span>
            </label>
            <input
              type="number"
              min={min}
              max={max}
              value={form[key]}
              onChange={(e) => handleChange(key, e.target.value)}
              className="input-field"
            />
            <input
              type="range"
              min={min}
              max={max}
              value={form[key]}
              onChange={(e) => handleChange(key, e.target.value)}
              className="w-full mt-1 accent-duke-blue"
            />
          </div>
        ))}

        {error && (
          <p className="text-sm text-red-500">{error.response?.data?.detail || 'Save failed.'}</p>
        )}

        <button
          onClick={() => saveGoals()}
          disabled={isPending}
          className="btn-primary w-full py-2.5"
        >
          {isPending ? 'Saving…' : 'Save Goals'}
        </button>

        {saved && (
          <p className="text-sm text-green-600 text-center font-medium">Goals saved!</p>
        )}
      </div>
    </div>
  )
}
