import { act, renderHook } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { loadFixture } from '../test/handlers'
import { useRoute } from './useRoute'
import type { RouteRequest } from '../api/types'

const VALID_REQ: RouteRequest = {
  lon: 137.4416,
  lat: -4.5895,
  material: 'hematita',
  sol: 1360,
  hora: 9,
  vmax: 1000,
}

describe('useRoute', () => {
  it('finds route successfully and updates state (happy)', async () => {
    const { result } = renderHook(() => useRoute())

    expect(result.current.loading).toBe(false)
    expect(result.current.route).toBeNull()
    expect(result.current.error).toBeNull()

    let res: unknown
    await act(async () => {
      res = await result.current.findRoute(VALID_REQ)
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.route).not.toBeNull()
    expect(result.current.route?.resumen.objetivo).toBe('Oudam')
    expect(res).toEqual(loadFixture('route.json'))
    expect(result.current.error).toBeNull()
  })

  it('cancels an in-flight route request without setting an error (edge)', async () => {
    server.use(
      http.post('/api/ruta', async () => {
        await new Promise((r) => setTimeout(r, 200))
        return HttpResponse.json(loadFixture('route.json'))
      }),
    )

    const { result } = renderHook(() => useRoute())

    act(() => {
      void result.current.findRoute(VALID_REQ)
    })
    expect(result.current.loading).toBe(true)

    act(() => {
      result.current.cancel()
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.route).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('handles 503 error, extracts detail and calls on503 callback (failure)', async () => {
    const on503 = vi.fn()
    server.use(
      http.post('/api/ruta', () => {
        return HttpResponse.json({ detail: 'Routing service unavailable' }, { status: 503 })
      }),
    )

    const { result } = renderHook(() => useRoute({ on503 }))

    await act(async () => {
      const res = await result.current.findRoute(VALID_REQ)
      expect(res).toBeNull()
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.route).toBeNull()
    expect(result.current.error).toBe('Routing service unavailable')
    expect(result.current.errorStatus).toBe(503)
    expect(on503).toHaveBeenCalledTimes(1)
  })

  it('handles 400 validation error and extracts detail (failure)', async () => {
    server.use(
      http.post('/api/ruta', () => {
        return HttpResponse.json({ detail: 'Origin is outside the AOI' }, { status: 400 })
      }),
    )

    const { result } = renderHook(() => useRoute())

    await act(async () => {
      await result.current.findRoute(VALID_REQ)
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe('Origin is outside the AOI')
    expect(result.current.errorStatus).toBe(400)
  })

  it('resets route and error state (happy)', async () => {
    const { result } = renderHook(() => useRoute())

    await act(async () => {
      await result.current.findRoute(VALID_REQ)
    })
    expect(result.current.route).not.toBeNull()

    act(() => {
      result.current.reset()
    })
    expect(result.current.route).toBeNull()
    expect(result.current.error).toBeNull()
  })
})
