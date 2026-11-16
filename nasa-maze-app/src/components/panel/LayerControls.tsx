import type { RasterBand } from '../../api/types'
import { bandLabel } from '../../domain/labels'
import type { ColorByMode } from '../map/Legend'

export interface LayerControlsProps {
  basemapOnline: boolean
  onToggleBasemap: (online: boolean) => void
  selectedBand: RasterBand | null
  onBandChange: (band: RasterBand | null) => void
  opacity: number
  onOpacityChange: (opacity: number) => void
  showTraverse: boolean
  onToggleTraverse: (show: boolean) => void
  colorBy: ColorByMode
  onColorByChange: (mode: ColorByMode) => void
  riskAvailable?: boolean
  rasterError?: string | null
}

const ALL_BANDS: RasterBand[] = [
  'pendiente_grados',
  'rugosidad_m',
  'fraccion_oscura',
  'inercia_termica_tiu',
  'albedo',
  'distancia_duna_m',
]

export function LayerControls({
  basemapOnline,
  onToggleBasemap,
  selectedBand,
  onBandChange,
  opacity,
  onOpacityChange,
  showTraverse,
  onToggleTraverse,
  colorBy,
  onColorByChange,
  riskAvailable = true,
  rasterError,
}: LayerControlsProps) {
  return (
    <div
      aria-label="Layer controls"
      data-testid="layer-controls"
      className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-slate-900/95 p-3 text-xs text-slate-100 shadow-lg"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
        <label className="flex cursor-pointer items-center gap-2 select-none">
          <input
            type="checkbox"
            aria-label="Online basemap"
            checked={basemapOnline}
            onChange={(e) => onToggleBasemap(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-cyan-600 focus:ring-1 focus:ring-cyan-500"
          />
          <span className="font-medium text-slate-200">Online basemap</span>
        </label>
      </div>

      <div className="flex flex-col gap-1.5 border-b border-slate-800 pb-2">
        <label htmlFor="raster-band-select" className="font-medium text-slate-300">
          Raster overlay
        </label>
        <select
          id="raster-band-select"
          aria-label="Raster band"
          value={selectedBand ?? ''}
          onChange={(e) => onBandChange(e.target.value ? (e.target.value as RasterBand) : null)}
          className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-100"
        >
          <option value="">None (off)</option>
          {ALL_BANDS.map((b) => (
            <option key={b} value={b}>
              {bandLabel(b)}
            </option>
          ))}
        </select>

        {selectedBand && (
          <div className="mt-1 flex items-center justify-between gap-2">
            <label htmlFor="raster-opacity" className="text-slate-400">
              Opacity: {Math.round(opacity * 100)}%
            </label>
            <input
              id="raster-opacity"
              aria-label="Raster opacity"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={opacity}
              onChange={(e) => onOpacityChange(Number(e.target.value))}
              className="h-1.5 w-24 cursor-pointer accent-cyan-500"
            />
          </div>
        )}

        {rasterError && (
          <span className="text-xs text-rose-400">{rasterError}</span>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
        <label className="flex cursor-pointer items-center gap-2 select-none">
          <input
            type="checkbox"
            aria-label="Curiosity traverse"
            checked={showTraverse}
            onChange={(e) => onToggleTraverse(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-cyan-600 focus:ring-1 focus:ring-cyan-500"
          />
          <span className="font-medium text-slate-200">Curiosity traverse</span>
        </label>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="font-medium text-slate-300">Color route by</span>
        <div className="grid grid-cols-3 gap-1 rounded bg-slate-950 p-0.5">
          <button
            type="button"
            onClick={() => onColorByChange('soil')}
            className={`rounded px-2 py-1 text-center font-medium transition ${
              colorBy === 'soil'
                ? 'bg-cyan-700 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Soil
          </button>
          <button
            type="button"
            onClick={() => onColorByChange('slope')}
            className={`rounded px-2 py-1 text-center font-medium transition ${
              colorBy === 'slope'
                ? 'bg-cyan-700 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Slope
          </button>
          {riskAvailable && (
            <button
              type="button"
              onClick={() => onColorByChange('risk')}
              className={`rounded px-2 py-1 text-center font-medium transition ${
                colorBy === 'risk'
                  ? 'bg-cyan-700 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Risk
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default LayerControls
