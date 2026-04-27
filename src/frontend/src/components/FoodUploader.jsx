import { useRef, useState } from 'react'
import api from '../api/client'
import ConfirmationCard from './ConfirmationCard'

/**
 * FoodUploader — drag-and-drop / click-to-upload image component.
 * Calls POST /identify and opens ConfirmationCard with results.
 */
export default function FoodUploader() {
  const inputRef              = useRef(null)
  const [dragging, setDrag]   = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [result, setResult]   = useState(null)   // { imageUrl, predictions }

  async function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      setError('Please upload a valid image file.')
      return
    }
    setError(null)
    setLoading(true)

    const imageUrl = URL.createObjectURL(file)
    const form = new FormData()
    form.append('file', file)

    try {
      const { data } = await api.post('/identify', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult({ imageUrl, predictions: data.predictions })
    } catch (err) {
      setError(err.response?.data?.detail || 'Identification failed. Try again.')
    } finally {
      setLoading(false)
    }
  }

  function onInputChange(e) {
    if (e.target.files[0]) handleFile(e.target.files[0])
  }

  function onDrop(e) {
    e.preventDefault()
    setDrag(false)
    handleFile(e.dataTransfer.files[0])
  }

  return (
    <>
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Identify a Meal
        </h2>

        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors select-none ${
            dragging
              ? 'border-duke-blue bg-blue-50'
              : 'border-gray-300 hover:border-duke-light hover:bg-gray-50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={onInputChange}
          />
          {loading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-4 border-duke-blue border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-gray-500">Identifying…</p>
            </div>
          ) : (
            <>
              <div className="text-4xl mb-2">📷</div>
              <p className="text-sm font-medium text-gray-700">
                Drag & drop a food photo or <span className="text-duke-blue underline">click to browse</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">JPEG, PNG, WebP — max 10 MB</p>
            </>
          )}
        </div>

        {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
      </div>

      {result && (
        <ConfirmationCard
          imageUrl={result.imageUrl}
          predictions={result.predictions}
          onClose={() => {
            URL.revokeObjectURL(result.imageUrl)
            setResult(null)
          }}
        />
      )}
    </>
  )
}
