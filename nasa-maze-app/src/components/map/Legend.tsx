import { riskLevelColor, riskLevelLabel, soilColor, soilLabel } from '../../domain/labels'
import { slopeColor } from '../../domain/routeView'

export type ColorByMode = 'soil' | 'slope' | 'risk'

export interface LegendProps {
  mode: ColorByMode
  soilTypes?: string[]
}

const SLOPE_BUCKETS = [
  { label: '< 5°', degrees: 0 },
  { label: '5–10°', degrees: 7 },
  { label: '10–15°', degrees: 12 },
  { label: '≥ 15°', degrees: 20 },
]

const RISK_LEVELS = ['low', 'medium', 'high', 'unknown']

const DEFAULT_SOILS = ['arena_dunas', 'lecho_rocoso_firme', 'regolito_compacto', 'rocoso_fracturado']

export function Legend({ mode, soilTypes = DEFAULT_SOILS }: LegendProps) {
  return (
    <div
      aria-label="Map legend"
      data-testid="map-legend"
      className="rounded-lg bg-slate-900/90 p-3 text-xs text-slate-100 shadow"
    >
      {mode === 'slope' && (
        <ul>
          {SLOPE_BUCKETS.map((bucket) => (
            <li key={bucket.label} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ background: slopeColor(bucket.degrees) }}
              />
              {bucket.label}
            </li>
          ))}
        </ul>
      )}
      {mode === 'soil' && (
        <ul>
          {soilTypes.map((soil) => (
            <li key={soil} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ background: soilColor(soil) }}
              />
              {soilLabel(soil)}
            </li>
          ))}
        </ul>
      )}
      {mode === 'risk' && (
        <ul>
          {RISK_LEVELS.map((level) => (
            <li key={level} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ background: riskLevelColor(level) }}
              />
              {riskLevelLabel(level)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default Legend
