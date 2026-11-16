import { useState } from 'react'
import type { HealthResponse, Material, RouteResponse } from '../../api/types'
import type { Capabilities } from '../../domain/capabilities'
import {
  BRADBURY,
  buildRouteRequest,
  MISSION_DEFAULTS,
  type MissionParams,
  validateMission,
} from '../../domain/mission'
import type { NamedPoint } from '../../domain/sites'
import { useRoute } from '../../hooks/useRoute'
import { MineralPicker } from './MineralPicker'
import { MissionSettings } from './MissionSettings'
import { OriginPicker, type OriginPoint } from './OriginPicker'

export interface RoutePanelProps {
  health: HealthResponse | null
  capabilities: Capabilities
  originOptions?: NamedPoint[]
  selectedOrigin?: OriginPoint
  onOriginChange?: (origin: OriginPoint) => void
  selectedMaterial?: Material
  onMaterialChange?: (material: Material) => void
  onRouteCalculated?: (route: RouteResponse) => void
  onRefetchHealth?: () => void
  className?: string
}

const DEFAULT_ORIGIN: OriginPoint = {
  lon: BRADBURY.lon,
  lat: BRADBURY.lat,
  nombre: BRADBURY.nombre,
}

export function RoutePanel({
  health,
  capabilities,
  originOptions = [],
  selectedOrigin,
  onOriginChange,
  selectedMaterial,
  onMaterialChange,
  onRouteCalculated,
  onRefetchHealth,
  className = '',
}: RoutePanelProps) {
  const [internalOrigin, setInternalOrigin] = useState<OriginPoint>(DEFAULT_ORIGIN)
  const [internalMaterial, setInternalMaterial] = useState<Material>('hematita')
  const [mission, setMission] = useState<MissionParams>(MISSION_DEFAULTS)

  const origin = selectedOrigin ?? internalOrigin
  const handleOriginChange = onOriginChange ?? setInternalOrigin

  const material = selectedMaterial ?? internalMaterial
  const handleMaterialChange = onMaterialChange ?? setInternalMaterial

  const { loading, error, findRoute, cancel } = useRoute({
    on503: onRefetchHealth,
  })

  const allowedSols = health?.sols ?? [1360, 2140, 3290, 4710]
  const missionErrors = validateMission(mission, allowedSols)
  const isMissionValid = Object.keys(missionErrors).length === 0
  const isRoutingUnavailable = capabilities.routing === 'none'

  const handleFindRoute = async () => {
    if (isRoutingUnavailable || !isMissionValid || loading) return

    const req = buildRouteRequest(origin, material, mission)
    const result = await findRoute(req)
    if (result) {
      onRouteCalculated?.(result)
    }
  }

  return (
    <div
      aria-label="Route planning panel"
      data-testid="route-panel"
      className={`w-full max-w-sm rounded-xl border border-slate-800 bg-slate-900/95 p-4 text-slate-100 shadow-xl backdrop-blur-md sm:w-90 ${className}`}
    >
      <div className="mb-3 flex items-center justify-between border-b border-slate-800 pb-2">
        <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase">
          Plan Route
        </h2>
        <span className="text-xs text-slate-400">Gale Crater</span>
      </div>

      <div className="flex flex-col gap-3">
        <OriginPicker
          value={origin}
          onChange={handleOriginChange}
          options={originOptions}
          originMode={capabilities.originMode}
          searchEnabled={capabilities.searchEnabled}
          disabled={loading}
        />

        <MineralPicker
          selected={material}
          onChange={handleMaterialChange}
          availableMaterials={capabilities.materials}
          disabled={loading || isRoutingUnavailable}
        />

        <MissionSettings
          mission={mission}
          onChange={setMission}
          allowedSols={allowedSols}
          disabled={!capabilities.missionEditable || loading}
          errors={missionErrors}
        />

        {error && (
          <div
            role="alert"
            className="rounded border border-rose-500/40 bg-rose-950/60 p-2 text-xs text-rose-200"
          >
            {error}
          </div>
        )}

        <div className="flex flex-col gap-2 pt-1">
          {loading ? (
            <div className="flex gap-2">
              <button
                type="button"
                disabled
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-cyan-800 px-4 py-2.5 text-xs font-semibold text-white shadow-md"
              >
                <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Finding route...
              </button>
              <button
                type="button"
                onClick={cancel}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={isRoutingUnavailable || !isMissionValid}
              onClick={handleFindRoute}
              className="flex w-full items-center justify-center rounded-lg bg-cyan-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md transition hover:bg-cyan-500 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Find route
            </button>
          )}

          {isRoutingUnavailable && (
            <p className="text-center text-xs text-rose-400/90">
              Routing engine unavailable
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default RoutePanel
