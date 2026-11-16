import type { ReactNode } from 'react'
import { MapContainer } from 'react-leaflet'

const AOI_BOUNDS: [[number, number], [number, number]] = [
  [-4.74, 137.345],
  [-4.58, 137.455],
]

export interface MarsMapProps {
  children?: ReactNode
}

export function MarsMap({ children }: MarsMapProps) {
  return (
    <div className="relative isolate h-full w-full" aria-label="Mars map" data-testid="mars-map">
      <MapContainer
        bounds={AOI_BOUNDS}
        className="h-full w-full bg-slate-950"
        preferCanvas={false}
      >
        {children}
      </MapContainer>
    </div>
  )
}

export default MarsMap
