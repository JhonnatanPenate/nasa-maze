import { useEffect, useRef } from 'react'
import { ImageOverlay } from 'react-leaflet'
import { useRasterBand } from '../../hooks/useRasterBand'
import type { RasterBand, RasterCmap } from '../../api/types'

export interface RasterOverlayProps {
  banda: RasterBand | null
  cmap?: RasterCmap
  opacity?: number
  onError?: (message: string | null) => void
}

export function RasterOverlay({ banda, cmap = 'viridis', opacity = 0.7, onError }: RasterOverlayProps) {
  const onErrorRef = useRef(onError)
  useEffect(() => {
    onErrorRef.current = onError
  })

  const { url, bounds, error } = useRasterBand(banda, cmap)

  useEffect(() => {
    onErrorRef.current?.(error)
  }, [error])

  if (!url || !bounds) return null

  const [w, s, e, n] = bounds
  return (
    <ImageOverlay
      url={url}
      bounds={[
        [s, w],
        [n, e],
      ]}
      opacity={opacity}
    />
  )
}

export default RasterOverlay
