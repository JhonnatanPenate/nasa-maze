import type { Material } from '../../api/types'
import { mineralLabel } from '../../domain/labels'

export interface MineralPickerProps {
  selected: Material
  onChange: (material: Material) => void
  availableMaterials?: Material[]
  disabled?: boolean
}

const ALL_MATERIALS: Material[] = ['hematita', 'esmectitas', 'tridimita', 'sulfatos']

export function MineralPicker({
  selected,
  onChange,
  availableMaterials = ALL_MATERIALS,
  disabled = false,
}: MineralPickerProps) {
  const sulfatesDisabled = !availableMaterials.includes('sulfatos')

  return (
    <div className="flex flex-col gap-1.5" data-testid="mineral-picker">
      <label htmlFor="mineral-select" className="text-xs font-semibold text-slate-300">
        To (Target mineral)
      </label>
      <select
        id="mineral-select"
        aria-label="Target mineral"
        value={selected}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as Material)}
        className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-sm text-slate-100 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {ALL_MATERIALS.map((mat) => {
          const isAvailable = availableMaterials.includes(mat)
          return (
            <option
              key={mat}
              value={mat}
              disabled={!isAvailable}
              title={!isAvailable ? 'Requires live routing engine' : undefined}
            >
              {mineralLabel(mat)}
            </option>
          )
        })}
      </select>
      {sulfatesDisabled && (
        <span
          className="text-xs text-amber-400/90"
          title="Requires live routing engine"
        >
          Sulfates requires live routing engine
        </span>
      )}
    </div>
  )
}

export default MineralPicker
