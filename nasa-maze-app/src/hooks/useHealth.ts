import { useEffect, useState } from 'react'
import { getHealth } from '../api/coreClient'
import type { HealthResponse } from '../api/types'

export interface UseHealthResult {
  health: HealthResponse | null
  loading: boolean
  error: string | null
  refetch: () => void
}

interface HealthState {
  token: number
  health: HealthResponse | null
  error: string | null
}

export function useHealth(): UseHealthResult {
  const [data, setData] = useState<HealthState>({
    token: 0,
    health: null,
    error: null,
  })
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then((res) => {
        if (controller.signal.aborted) return
        setData({ token: reloadToken, health: res, error: null })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        const message = err instanceof Error ? err.message : 'Failed to load health'
        setData({ token: reloadToken, health: null, error: message })
      })
    return () => controller.abort()
  }, [reloadToken])

  const loading = data.token !== reloadToken || (data.health === null && data.error === null)

  return {
    health: data.health,
    loading,
    error: data.error,
    refetch: () => setReloadToken((t) => t + 1),
  }
}
