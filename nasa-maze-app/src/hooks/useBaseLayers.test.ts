import { renderHook, waitFor } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useBaseLayers } from './useBaseLayers'

describe('useBaseLayers', () => {
  it('loads base layers happy path', async () => {
    const { result } = renderHook(() => useBaseLayers())
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.layers?.type).toBe('FeatureCollection')
    expect(result.current.layers?.features.length).toBeGreaterThan(0)
  })

  it('handles empty feature collection (edge)', async () => {
    server.use(
      http.get('/api/capas/base', () => HttpResponse.json({ type: 'FeatureCollection', features: [] })),
    )
    const { result } = renderHook(() => useBaseLayers())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.layers?.features).toHaveLength(0)
    expect(result.current.error).toBeNull()
  })

  it('reports error on failure', async () => {
    server.use(
      http.get('/api/capas/base', () => HttpResponse.json({ detail: 'down' }, { status: 503 })),
    )
    const { result } = renderHook(() => useBaseLayers())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeTruthy()
    expect(result.current.layers).toBeNull()
  })

  it('handles unmount gracefully while loading is in flight (major)', () => {
    const { result, unmount } = renderHook(() => useBaseLayers())
    expect(result.current.loading).toBe(true)
    unmount()
  })
})
