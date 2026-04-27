import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '../api/client'

/**
 * ConfirmationCard — modal shown after /identify returns results.
 *
 * Props:
 *   imageUrl    — object URL for the uploaded photo thumbnail
 *   predictions — array from POST /identify response
 *   onClose     — callback to dismiss the card
 */
export default function ConfirmationCard({ imageUrl, predictions, onClose }) {
  const queryClient = useQueryClient()

  // Default selection: first Duke match of the highest-confidence prediction
  const [selectedPredIdx, setSelectedPredIdx]   = useState(0)
  const [selectedMatchIdx, setSelectedMatchIdx] = useState(0)
  const [multiplier, setMultiplier]             = useState(1.0)

  const activePred  = predictions[selectedPredIdx]
  const activeMatch = activePred?.duke_matches?.[selectedMatchIdx]

  const { mutate: logMeal, isPending, error } = useMutation({
    mutationFn: () =>
      api.post('/log', {
        food_name:          activePred.predicted_class,
        duke_item_name:     activeMatch.food_name,
        dining_location:    activeMatch.dining_location,
        calories:           activeMatch.calories,
        protein_g:          activeMatch.protein_g,
        carbs_g:            activeMatch.carbs_g,
        fat_g:              activeMatch.fat_g,
        serving_multiplier: multiplier,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="bg-duke-navy px-5 py-4 flex items-center justify-between">
          <h2 className="text-white font-semibold">Confirm Meal</h2>
          <button onClick={onClose} className="text-blue-200 hover:text-white text-xl leading-none">&times;</button>
        </div>

        <div className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
          {/* Thumbnail + classifier result */}
          <div className="flex gap-4 items-start">
            {imageUrl && (
              <img src={imageUrl} alt="Uploaded food" className="w-24 h-24 object-cover rounded-xl flex-shrink-0" />
            )}
            <div className="flex-1">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Detected food</p>
              {predictions.map((pred, pi) => (
                <label key={pi} className="flex items-center gap-2 mb-1 cursor-pointer">
                  <input
                    type="radio"
                    name="pred"
                    checked={selectedPredIdx === pi}
                    onChange={() => { setSelectedPredIdx(pi); setSelectedMatchIdx(0) }}
                    className="accent-duke-blue"
                  />
                  <span className="text-sm font-medium capitalize">{pred.predicted_class}</span>
                  <span className="text-xs text-gray-400">({(pred.confidence * 100).toFixed(1)}%)</span>
                </label>
              ))}
            </div>
          </div>

          {/* Duke menu matches */}
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Duke menu match</p>
            <div className="space-y-2">
              {activePred?.duke_matches?.map((match, mi) => (
                <label
                  key={mi}
                  className={`flex items-start gap-3 border rounded-lg p-3 cursor-pointer transition-colors ${
                    selectedMatchIdx === mi
                      ? 'border-duke-blue bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="match"
                    checked={selectedMatchIdx === mi}
                    onChange={() => setSelectedMatchIdx(mi)}
                    className="mt-0.5 accent-duke-blue"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{match.food_name}</p>
                    <p className="text-xs text-gray-400">{match.dining_location} · sim {(match.similarity * 100).toFixed(0)}%</p>
                    <div className="flex gap-3 mt-1 text-xs text-gray-600">
                      <span>{match.calories} kcal</span>
                      <span>{match.protein_g}g P</span>
                      <span>{match.carbs_g}g C</span>
                      <span>{match.fat_g}g F</span>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Serving multiplier */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700 whitespace-nowrap">Serving size ×</label>
            <input
              type="number"
              min="0.25"
              max="10"
              step="0.25"
              value={multiplier}
              onChange={(e) => setMultiplier(parseFloat(e.target.value) || 1)}
              className="input-field w-24"
            />
            {activeMatch && (
              <p className="text-sm text-gray-500">
                = {Math.round(activeMatch.calories * multiplier)} kcal
              </p>
            )}
          </div>

          {error && (
            <p className="text-sm text-red-500">{error.response?.data?.detail || 'Failed to log meal.'}</p>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 py-4 border-t flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={() => logMeal()}
            disabled={!activeMatch || isPending}
            className="btn-primary"
          >
            {isPending ? 'Logging…' : 'Log This Meal'}
          </button>
        </div>
      </div>
    </div>
  )
}
