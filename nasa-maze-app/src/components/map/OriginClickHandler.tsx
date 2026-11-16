import { useMapEvents } from 'react-leaflet'
import { isInsideAoi } from '../../domain/mission'

const GALE_AOI: readonly [number, number, number, number] = [137.345, -4.74, 137.455, -4.58]

export interface ClickOriginPoint {
  lon: number
  lat: number
  nombre: string
}

export interface OriginClickHandlerProps {
  enabled?: boolean
  aoi?: readonly [number, number, number, number]
  onSelectOrigin: (point: ClickOriginPoint) => void
}

export function OriginClickHandler({
  enabled = true,
  aoi = GALE_AOI,
  onSelectOrigin,
}: OriginClickHandlerProps) {
  useMapEvents({
    click(e) {
      if (!enabled) return
      const lon = e.latlng.lng
      const lat = e.latlng.lat
      if (isInsideAoi(lon, lat, aoi)) {
        onSelectOrigin({
          lon,
          lat,
          nombre: `Map point (${lon.toFixed(4)}, ${lat.toFixed(4)})`,
        })
      }
    },
  })

  return null
}

export default OriginClickHandler
