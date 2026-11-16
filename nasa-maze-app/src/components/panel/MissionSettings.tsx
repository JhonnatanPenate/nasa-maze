import { useState } from 'react'
import type { MissionErrors, MissionParams } from '../../domain/mission'

export interface MissionSettingsProps {
  mission: MissionParams
  onChange: (mission: MissionParams) => void
  allowedSols?: number[]
  disabled?: boolean
  defaultExpanded?: boolean
  errors?: MissionErrors
}

const DEFAULT_SOLS = [1360, 2140, 3290, 4710]

export function MissionSettings({
  mission,
  onChange,
  allowedSols = DEFAULT_SOLS,
  disabled = false,
  defaultExpanded = false,
  errors,
}: MissionSettingsProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="rounded border border-slate-700/80 bg-slate-800/60 p-2 text-xs text-slate-200">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between font-medium text-slate-300 hover:text-white"
      >
        <span>Mission settings</span>
        <span className="text-slate-400">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="mt-3 flex flex-col gap-2.5 border-t border-slate-700/60 pt-2.5">
          <div className="flex flex-col gap-1">
            <label htmlFor="mission-sol" className="font-medium text-slate-300">
              Sol
            </label>
            <select
              id="mission-sol"
              aria-label="Sol"
              value={mission.sol}
              disabled={disabled}
              onChange={(e) => onChange({ ...mission, sol: Number(e.target.value) })}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {allowedSols.map((s) => (
                <option key={s} value={s}>
                  Sol {s}
                </option>
              ))}
            </select>
            {errors?.sol && <p className="text-xs text-rose-400">{errors.sol}</p>}
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="mission-hora" className="font-medium text-slate-300">
              Start hour (LMST)
            </label>
            <input
              id="mission-hora"
              aria-label="Start hour (LMST)"
              type="number"
              min="0"
              max="23.5"
              step="0.5"
              value={mission.hora}
              disabled={disabled}
              onChange={(e) => onChange({ ...mission, hora: Number(e.target.value) })}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            />
            {errors?.hora && <p className="text-xs text-rose-400">{errors.hora}</p>}
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="mission-vmax" className="font-medium text-slate-300">
              Max speed (m/h)
            </label>
            <input
              id="mission-vmax"
              aria-label="Max speed (m/h)"
              type="number"
              min="1"
              value={mission.vmax}
              disabled={disabled}
              onChange={(e) => onChange({ ...mission, vmax: Number(e.target.value) })}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            />
            {errors?.vmax && <p className="text-xs text-rose-400">{errors.vmax}</p>}
          </div>
        </div>
      )}
    </div>
  )
}

export default MissionSettings
