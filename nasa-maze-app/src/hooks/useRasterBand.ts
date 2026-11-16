import { useEffect, useRef, useState } from 'react'
import { getRasterBand } from '../api/coreClient'
import type { RasterBand, RasterCmap } from '../api/types'

export interface UseRasterBandResult {
  url: string | null
  bounds: [number, number, number, number] | null
  loading: boolean
  error: string | null
}

interface RasterState {
  key: string
  url: string | null
  bounds: [number, number, number, number] | null
  error: string | null
}

export function useRasterBand(
  banda: RasterBand | null,
  cmap: RasterCmap = 'viridis',
): UseRasterBandResult {
  const [state, setState] = useState<RasterState | null>(null)
  const [prevBanda, setPrevBanda] = useState<RasterBand | null>(banda)
  const activeUrlRef = useRef<string | null>(null)

  if (prevBanda !== banda) {
    setPrevBanda(banda)
    if (!banda) {
      setState(null)
    }
  }

  const currentKey = banda ? `${banda}:${cmap}` : null

  useEffect(() => {
    if (!banda) {
      if (activeUrlRef.current) {
        URL.revokeObjectURL(activeUrlRef.current)
        activeUrlRef.current = null
      }
      return
    }
    const controller = new AbortController()
    const key = `${banda}:${cmap}`

    getRasterBand(banda, cmap, controller.signal)
      .then((res) => {
        if (controller.signal.aborted) {
          URL.revokeObjectURL(res.url)
          return
        }
        if (activeUrlRef.current && activeUrlRef.current !== res.url) {
          URL.revokeObjectURL(activeUrlRef.current)
        }
        activeUrlRef.current = res.url
        setState({ key, url: res.url, bounds: res.bounds, error: null })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        if (activeUrlRef.current) {
          URL.revokeObjectURL(activeUrlRef.current)
          activeUrlRef.current = null
        }
        const message = err instanceof Error ? err.message : 'Failed to load raster band'
        setState({ key, url: null, bounds: null, error: message })
      })

    return () => {
      controller.abort()
    }
  }, [banda, cmap])

  // Revoke active URL on unmount
  useEffect(() => {
    return () => {
      if (activeUrlRef.current) {
        URL.revokeObjectURL(activeUrlRef.current)
        activeUrlRef.current = null
      }
    }
  }, [])

  if (!banda) {
    return { url: null, bounds: null, loading: false, error: null }
  }

  const isCurrent = state?.key === currentKey
  const loading = !isCurrent
  const url = isCurrent ? state.url : (state?.url ?? null)
  const bounds = isCurrent ? state.bounds : (state?.bounds ?? null)
  const error = isCurrent ? state.error : null

  return { url, bounds, loading, error }
}
