import { type FormEvent, useState } from 'react'
import { searchPlaces } from '../../api/coreClient'
import type { Place } from '../../api/types'
import type { OriginMode } from '../../domain/capabilities'
import { BRADBURY } from '../../domain/mission'
import type { NamedPoint } from '../../domain/sites'

export interface OriginPoint {
  lon: number
  lat: number
  nombre?: string
}

export interface OriginPickerProps {
  value: OriginPoint
  onChange: (point: OriginPoint) => void
  options?: NamedPoint[]
  originMode?: OriginMode
  searchEnabled?: boolean
  disabled?: boolean
}

const DEFAULT_OPTIONS: NamedPoint[] = [
  { nombre: BRADBURY.nombre, lon: BRADBURY.lon, lat: BRADBURY.lat },
]

export function OriginPicker({
  value,
  onChange,
  options = DEFAULT_OPTIONS,
  originMode = 'free',
  searchEnabled = false,
  disabled = false,
}: OriginPickerProps) {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Place[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const isLocked = originMode === 'bradbury'
  const isNone = originMode === 'none'
  const isControlDisabled = disabled || isLocked || isNone

  const matchingOption = options.find(
    (opt) =>
      Math.abs(opt.lon - value.lon) < 0.0001 &&
      Math.abs(opt.lat - value.lat) < 0.0001,
  )

  const isCustom = !matchingOption
  const currentSelectValue = matchingOption
    ? `${matchingOption.lon},${matchingOption.lat}`
    : `${value.lon},${value.lat}`

  const handleSelectOption = (coordString: string) => {
    const found = options.find((opt) => `${opt.lon},${opt.lat}` === coordString)
    if (found) {
      onChange(found)
    }
  }

  const handleSearchSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsSearching(true)
    setSearchError(null)
    try {
      const res = await searchPlaces(query.trim())
      setSearchResults(res.results.map((r) => r.place))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Search failed'
      setSearchError(msg)
    } finally {
      setIsSearching(false)
    }
  }

  const handleSelectPlace = (place: Place) => {
    onChange({
      lon: place.center.lon,
      lat: place.center.lat,
      nombre: place.name,
    })
    setSearchResults([])
    setQuery('')
  }

  return (
    <div className="flex flex-col gap-2" data-testid="origin-picker">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="origin-select" className="text-xs font-semibold text-slate-300">
          From (Origin)
        </label>
        <select
          id="origin-select"
          aria-label="Origin location"
          value={currentSelectValue}
          disabled={isControlDisabled}
          onChange={(e) => handleSelectOption(e.target.value)}
          className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-sm text-slate-100 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {options.map((opt) => (
            <option key={`${opt.lon},${opt.lat}`} value={`${opt.lon},${opt.lat}`}>
              {opt.nombre}
            </option>
          ))}
          {isCustom && (
            <option value={`${value.lon},${value.lat}`}>
              {value.nombre ?? `Custom (${value.lon.toFixed(4)}, ${value.lat.toFixed(4)})`}
            </option>
          )}
        </select>
      </div>

      {isLocked && (
        <span className="text-xs text-amber-400/90">
          Locked to Bradbury Landing in fallback mode
        </span>
      )}

      {searchEnabled && !isLocked && !isNone && (
        <div className="flex flex-col gap-1.5">
          <form onSubmit={handleSearchSubmit} className="flex gap-1.5">
            <input
              type="search"
              aria-label="Search origin place"
              placeholder="Search places (e.g. Glen Etive)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={disabled}
              className="flex-1 rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-100 placeholder-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={disabled || isSearching}
              className="rounded bg-cyan-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSearching ? '...' : 'Search'}
            </button>
          </form>

          {searchError && (
            <span className="text-xs text-rose-400">{searchError}</span>
          )}

          {searchResults.length > 0 && (
            <ul
              aria-label="Search results"
              role="listbox"
              className="max-h-28 overflow-y-auto rounded border border-slate-700 bg-slate-800/95 p-1 text-xs"
            >
              {searchResults.map((place) => (
                <li key={place.id}>
                  <button
                    type="button"
                    onClick={() => handleSelectPlace(place)}
                    className="w-full rounded px-2 py-1 text-left text-slate-200 hover:bg-cyan-900/50 hover:text-cyan-200"
                  >
                    {place.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default OriginPicker
