import { act, renderHook, waitFor } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useHealth } from './useHealth'

describe('useHealth', () => {
  it('loads health happy path', async () => {
    const { result } = renderHook(() => useHealth())
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.health?.servicios.ms6).toBe('ok')
    expect(result.current.error).toBeNull()
  })

  it('refetch reloads health (edge)', async () => {
    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    const first = result.current.health
    result.current.refetch()
    await waitFor(() => expect(result.current.health).not.toBe(first))
    expect(result.current.health).not.toBeNull()
  })

  it('reports error on failure', async () => {
    server.use(
      http.get('/api/health', () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
    )
    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeTruthy()
    expect(result.current.health).toBeNull()
  })

  it('sets loading immediately upon refetch without microtask delay (major)', async () => {
    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.loading).toBe(false)
    act(() => {
      result.current.refetch()
    })
    expect(result.current.loading).toBe(true)
  })

  it('does not crash or set state after unmount (major)', () => {
    const { result, unmount } = renderHook(() => useHealth())
    expect(result.current.loading).toBe(true)
    unmount()
  })
})
