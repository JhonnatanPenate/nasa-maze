import { useEffect } from 'react'
import { CircleMarker, Polyline, Popup, useMap } from 'react-leaflet'
import { soilColor, soilLabel } from '../../domain/labels'
import { riskScoreColor, riskScoreLevel, slopeColor, type RouteView } from '../../domain/routeView'
import type { ColorByMode } from './Legend'

export interface RouteLayerProps {
  view: RouteView
  colorBy: ColorByMode
  alternativeSelected?: boolean
  onSelectAlternative?: (selected: boolean) => void
}

type LonLat = [number, number]
const flip = (line: LonLat[]) => line.map(([lon, lat]) => [lat, lon] as [number, number])

interface Piece {
  coords: LonLat[]
  color: string
  info: string[]
}

function pieces(view: RouteView, colorBy: ColorByMode): Piece[] {
  if (colorBy === 'risk' && view.riskSegments.length > 0) {
    return view.riskSegments.map((s, i) => ({
      coords: [s.from, s.to],
      color: riskScoreColor(s.risk),
      info: [
        `Segment ${i + 1}`,
        `Risk: ${s.risk === null ? 'n/a' : s.risk.toFixed(2)} (${riskScoreLevel(s.risk)})`,
        ...(s.blocking ? ['Blocking'] : []),
        ...s.warnings,
      ],
    }))
  }
  return view.segments.map((s, i) => ({
    coords: s.coordinates,
    color: colorBy === 'soil' ? soilColor(s.tipo_suelo) : slopeColor(s.inclinacion_grados),
    info: [`Segment ${i + 1}`, `Soil: ${soilLabel(s.tipo_suelo)}`, `Slope: ${s.inclinacion_grados}°`],
  }))
}

function FitBounds({ bounds }: { bounds: RouteView['bounds'] }) {
  const map = useMap()
  useEffect(() => {
    const [w, s, e, n] = bounds
    map.fitBounds([[s, w], [n, e]], { padding: [60, 60] })
  }, [map, bounds])
  return null
}

export function RouteLayer({ view, colorBy, alternativeSelected = false, onSelectAlternative }: RouteLayerProps) {
  const alt = view.alternative
  const main = pieces(view, colorBy)
  const altPositions = alt ? flip(alt.coordinates) : null
  const altHandlers = { click: () => onSelectAlternative?.(!alternativeSelected) }

  return (
    <>
      <FitBounds bounds={view.bounds} />
      {altPositions && (
        <Polyline
          positions={altPositions}
          pathOptions={
            alternativeSelected
              ? { color: '#38bdf8', weight: 6, opacity: 0.9 }
              : { color: '#9ca3af', weight: 4, opacity: 0.7, dashArray: '8 8' }
          }
          eventHandlers={altHandlers}
        >
          <Popup>Alternative: {alt?.nombre}</Popup>
        </Polyline>
      )}
      {main.map((p, i) => (
        <Polyline
          key={`casing-${i}`}
          positions={flip(p.coords)}
          pathOptions={{ color: '#ffffff', weight: 10, opacity: alternativeSelected ? 0.3 : 1, lineCap: 'round' }}
          interactive={false}
        />
      ))}
      {main.map((p, i) => (
        <Polyline
          key={`line-${i}`}
          positions={flip(p.coords)}
          pathOptions={{ color: p.color, weight: 6, opacity: alternativeSelected ? 0.4 : 1, lineCap: 'round' }}
        >
          <Popup>
            {p.info.map((l) => (
              <div key={l}>{l}</div>
            ))}
          </Popup>
        </Polyline>
      ))}
      {view.origin && (
        <CircleMarker center={[view.origin.lat, view.origin.lon]} radius={7} pathOptions={{ color: '#fff', fillColor: '#0ea5e9', fillOpacity: 1 }}>
          <Popup>Origin: {view.origin.nombre}</Popup>
        </CircleMarker>
      )}
      {view.target && (
        <CircleMarker center={[view.target.lat, view.target.lon]} radius={7} pathOptions={{ color: '#fff', fillColor: '#f97316', fillOpacity: 1 }}>
          <Popup>Target: {view.target.nombre}</Popup>
        </CircleMarker>
      )}
    </>
  )
}

export default RouteLayer
