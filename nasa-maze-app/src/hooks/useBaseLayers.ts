import { useEffect, useState } from 'react'
import { getBaseLayers } from '../api/coreClient'
import type { BaseLayersResponse } from '../api/types'

export interface UseBaseLayersResult {
  layers: BaseLayersResponse | null
  loading: boolean
  error: string | null
}

interface BaseLayersState {
  layers: BaseLayersResponse | null
  error: string | null
}

export function useBaseLayers(): UseBaseLayersResult {
  const [data, setData] = useState<BaseLayersState | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    getBaseLayers(controller.signal)
      .then((res) => {
        if (controller.signal.aborted) return
        setData({ layers: res, error: null })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        const message = err instanceof Error ? err.message : 'Failed to load base layers'
        setData({ layers: null, error: message })
      })
    return () => controller.abort()
  }, [])

  return {
    layers: data?.layers ?? null,
    loading: data === null,
    error: data?.error ?? null,
  }
}
