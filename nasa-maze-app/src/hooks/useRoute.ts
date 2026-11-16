import { useCallback, useEffect, useRef, useState } from 'react'
import { CoreError, postRoute } from '../api/coreClient'
import type { RouteRequest, RouteResponse } from '../api/types'

export interface UseRouteOptions {
  on503?: () => void
}

export interface UseRouteResult {
  route: RouteResponse | null
  loading: boolean
  error: string | null
  errorStatus: number | null
  findRoute: (req: RouteRequest) => Promise<RouteResponse | null>
  cancel: () => void
  reset: () => void
}

export function useRoute(options?: UseRouteOptions): UseRouteResult {
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)

  const controllerRef = useRef<AbortController | null>(null)
  const on503Ref = useRef(options?.on503)
  useEffect(() => {
    on503Ref.current = options?.on503
  }, [options?.on503])

  const cancel = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort()
      controllerRef.current = null
    }
    setLoading(false)
  }, [])

  const reset = useCallback(() => {
    cancel()
    setRoute(null)
    setError(null)
    setErrorStatus(null)
  }, [cancel])

  const findRoute = useCallback(
    async (req: RouteRequest): Promise<RouteResponse | null> => {
      cancel()
      const controller = new AbortController()
      controllerRef.current = controller
      setLoading(true)
      setError(null)
      setErrorStatus(null)

      try {
        const result = await postRoute(req, controller.signal)
        if (controller.signal.aborted) return null
        setRoute(result)
        setLoading(false)
        return result
      } catch (err: unknown) {
        if (controller.signal.aborted) return null
        setLoading(false)
        if (err instanceof CoreError) {
          setError(err.detail)
          setErrorStatus(err.status)
          if (err.status === 503) {
            on503Ref.current?.()
          }
        } else if (err instanceof Error) {
          setError(err.message)
        } else {
          setError('Unexpected routing error')
        }
        return null
      }
    },
    [cancel],
  )

  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort()
      }
    }
  }, [])

  return {
    route,
    loading,
    error,
    errorStatus,
    findRoute,
    cancel,
    reset,
  }
}
