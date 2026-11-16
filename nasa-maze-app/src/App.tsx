import { useMemo, useState } from 'react'
import type { Material, RasterBand, RouteResponse } from './api/types'
import { MarsMap } from './components/map/MarsMap'
import { Basemap, type BasemapMode } from './components/map/Basemap'
import { RasterOverlay } from './components/map/RasterOverlay'
import { SitesLayer } from './components/map/SitesLayer'
import { RouteLayer } from './components/map/RouteLayer'
import { OriginClickHandler } from './components/map/OriginClickHandler'
import { Legend, type ColorByMode } from './components/map/Legend'
import { RoutePanel } from './components/panel/RoutePanel'
import { RouteSummary } from './components/panel/RouteSummary'
import { StatusBadge } from './components/panel/StatusBadge'
import { LayerControls } from './components/panel/LayerControls'
import type { OriginPoint } from './components/panel/OriginPicker'
import { capabilitiesFromHealth, type Capabilities } from './domain/capabilities'
import { BRADBURY } from './domain/mission'
import { buildRouteView, type RouteView } from './domain/routeView'
import { originOptions } from './domain/sites'
import { useBaseLayers } from './hooks/useBaseLayers'
import { useHealth } from './hooks/useHealth'

const DEFAULT_CAPABILITIES: Capabilities = {
  routing: 'none',
  originMode: 'none',
  materials: [],
  missionEditable: false,
  searchEnabled: false,
  riskEnabled: false,
}

const DEFAULT_ORIGIN: OriginPoint = {
  lon: BRADBURY.lon,
  lat: BRADBURY.lat,
  nombre: BRADBURY.nombre,
}

export default function App() {
  const { health, refetch: refetchHealth } = useHealth()
  const { layers } = useBaseLayers()

  const [basemapMode, setBasemapMode] = useState<BasemapMode | null>(null)
  const basemapOnline = basemapMode === 'online'
  const [selectedBand, setSelectedBand] = useState<RasterBand | null>(null)
  const [rasterOpacity, setRasterOpacity] = useState(0.7)
  const [rasterError, setRasterError] = useState<string | null>(null)
  const [showTraverse, setShowTraverse] = useState(true)
  const [colorBy, setColorBy] = useState<ColorByMode>('slope')

  const [selectedOrigin, setSelectedOrigin] = useState<OriginPoint>(DEFAULT_ORIGIN)
  const [selectedMaterial, setSelectedMaterial] = useState<Material>('hematita')
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [showAlternative, setShowAlternative] = useState(false)
  const routeView = useMemo<RouteView | null>(() => {
    if (!route) return null
    try {
      return buildRouteView(route)
    } catch {
      return null
    }
  }, [route])

  const capabilities = health ? capabilitiesFromHealth(health) : DEFAULT_CAPABILITIES
  const originOpts = layers ? originOptions(layers) : []

  const handleBasemapModeChange = (mode: BasemapMode) => {
    setBasemapMode(mode)
  }

  const handleToggleBasemap = (online: boolean) => {
    setBasemapMode(online ? 'online' : 'offline')
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      <div data-testid="map-container" className="absolute inset-0">
        <MarsMap>
          <Basemap
            mode={basemapMode ?? undefined}
            onModeChange={handleBasemapModeChange}
          />
          <RasterOverlay
            banda={selectedBand}
            opacity={rasterOpacity}
            onError={setRasterError}
          />
          {layers && (
            <SitesLayer
              layers={layers}
              material={selectedMaterial}
              showTraverse={showTraverse}
            />
          )}
          {routeView && (
            <RouteLayer
              view={routeView}
              colorBy={colorBy === 'risk' && routeView.riskSegments.length === 0 ? 'slope' : colorBy}
              alternativeSelected={showAlternative}
              onSelectAlternative={setShowAlternative}
            />
          )}
          <OriginClickHandler
            enabled={capabilities.originMode === 'free'}
            aoi={health?.aoi}
            onSelectOrigin={(pt) => setSelectedOrigin(pt)}
          />
        </MarsMap>
      </div>

      <div className="pointer-events-none absolute inset-0 z-10 flex flex-col justify-between p-4">
        <div className="flex items-start justify-between gap-4">
          <aside className="pointer-events-auto">
            {routeView && (
              <RouteSummary
                view={routeView}
                onNewRoute={() => setRoute(null)}
                showAlternative={showAlternative}
                onToggleAlternative={setShowAlternative}
              />
            )}
            <div className={routeView ? 'hidden' : ''}>
              <RoutePanel
                health={health}
                capabilities={capabilities}
                originOptions={originOpts}
                selectedOrigin={selectedOrigin}
                onOriginChange={setSelectedOrigin}
                selectedMaterial={selectedMaterial}
                onMaterialChange={setSelectedMaterial}
                onRouteCalculated={(r) => {
                  setShowAlternative(false)
                  setRoute(r)
                }}
                onRefetchHealth={refetchHealth}
              />
            </div>
          </aside>

          <header className="pointer-events-auto">
            <StatusBadge
              routingMode={capabilities.routing}
              basemapOnline={basemapOnline}
            />
          </header>
        </div>

        <div className="flex items-end justify-end gap-3">
          <aside className="pointer-events-auto flex flex-col items-end gap-2">
            <LayerControls
              basemapOnline={basemapOnline}
              onToggleBasemap={handleToggleBasemap}
              selectedBand={selectedBand}
              onBandChange={setSelectedBand}
              opacity={rasterOpacity}
              onOpacityChange={setRasterOpacity}
              showTraverse={showTraverse}
              onToggleTraverse={setShowTraverse}
              colorBy={colorBy}
              onColorByChange={setColorBy}
              riskAvailable={capabilities.riskEnabled}
              rasterError={rasterError}
            />
            <Legend mode={colorBy} />
          </aside>
        </div>
      </div>
    </div>
  )
}
