import L from 'leaflet'
import { Marker, Polyline } from 'react-leaflet'
import type { BaseLayersResponse, Material } from '../../api/types'
import { bradburyOrigin, candidateSites, chemSites, mslTraverse } from '../../domain/sites'

export interface SitesLayerProps {
  layers: BaseLayersResponse
  material: Material | null
  showTraverse?: boolean
}

function siteIcon(name: string, highlighted: boolean): L.DivIcon {
  const color = highlighted ? '#f97316' : '#38bdf8'
  const size = highlighted ? 14 : 10
  return L.divIcon({
    className: 'nasa-site-icon',
    html: `<span role="img" aria-label="${name}" title="${name}" style="display:block;width:${size}px;height:${size}px;border-radius:9999px;background:${color};border:1px solid white"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

export function SitesLayer({ layers, material, showTraverse = true }: SitesLayerProps) {
  const sites = chemSites(layers)
  const candidates = material ? new Set(candidateSites(sites, material).map((s) => s.nombre)) : new Set<string>()
  const bradbury = bradburyOrigin(layers)
  const traverse = mslTraverse(layers)

  return (
    <>
      {bradbury && (
        <Marker
          position={[bradbury.lat, bradbury.lon]}
          icon={siteIcon(bradbury.nombre, false)}
          title={bradbury.nombre}
        />
      )}
      {sites.map((site) => (
        <Marker
          key={site.nombre}
          position={[site.lat, site.lon]}
          icon={siteIcon(site.nombre, candidates.has(site.nombre))}
          title={site.nombre}
        />
      ))}
      {showTraverse &&
        traverse.map((line, i) => (
          <Polyline
            key={i}
            positions={line.map(([lon, lat]) => [lat, lon])}
            pathOptions={{ color: '#94a3b8', weight: 2, dashArray: '4 4' }}
          />
        ))}
    </>
  )
}

export default SitesLayer
