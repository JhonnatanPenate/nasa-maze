import { renderHook, waitFor } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { useRasterBand } from './useRasterBand'

describe('useRasterBand', () => {
  it('loads a raster band happy path', async () => {
    const { result } = renderHook(() => useRasterBand('pendiente_grados'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.url).toMatch(/^blob:/)
    expect(result.current.bounds).toEqual([137.345, -4.74, 137.455, -4.58])
    expect(result.current.error).toBeNull()
  })

  it('returns null state when banda is null (edge)', () => {
    const { result } = renderHook(() => useRasterBand(null))
    expect(result.current.loading).toBe(false)
    expect(result.current.url).toBeNull()
    expect(result.current.bounds).toBeNull()
  })

  it('reports error on 502', async () => {
    server.use(
      http.get('/api/capas/raster/:banda', () =>
        HttpResponse.json({ detail: 'raster unreadable' }, { status: 502 }),
      ),
    )
    const { result } = renderHook(() => useRasterBand('pendiente_grados'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeTruthy()
    expect(result.current.url).toBeNull()
  })

  it('keeps previous objectURL until new band finishes loading on band change (blocker)', async () => {
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL')
    const { result, rerender } = renderHook(
      ({ band }: { band: 'pendiente_grados' | 'rugosidad_m' | null }) => useRasterBand(band),
      { initialProps: { band: 'pendiente_grados' as 'pendiente_grados' | 'rugosidad_m' | null } },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))
    const firstUrl = result.current.url
    expect(firstUrl).toBeTruthy()
    expect(revokeSpy).not.toHaveBeenCalled()

    rerender({ band: 'rugosidad_m' })
    expect(result.current.loading).toBe(true)
    expect(revokeSpy).not.toHaveBeenCalledWith(firstUrl)

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.url).not.toBe(firstUrl)
    expect(revokeSpy).toHaveBeenCalledWith(firstUrl)
  })

  it('sets loading immediately when band changes from null to a band (major/minor)', () => {
    const { result, rerender } = renderHook(
      ({ band }: { band: 'pendiente_grados' | null }) => useRasterBand(band),
      { initialProps: { band: null as 'pendiente_grados' | null } },
    )
    expect(result.current.loading).toBe(false)
    rerender({ band: 'pendiente_grados' })
    expect(result.current.loading).toBe(true)
  })
})
