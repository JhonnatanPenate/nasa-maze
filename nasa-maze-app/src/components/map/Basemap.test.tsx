import { render, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MarsMap } from './MarsMap'
import { Basemap } from './Basemap'

class MockImage {
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  behavior: 'ok' | 'fail'
  constructor() {
    this.behavior = (globalThis as unknown as { __imageBehavior: 'ok' | 'fail' }).__imageBehavior
  }
  set src(_value: string) {
    queueMicrotask(() => {
      if (this.behavior === 'ok') this.onload?.()
      else this.onerror?.()
    })
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Basemap', () => {
  it('renders online tiles when the probe succeeds (happy)', async () => {
    ;(globalThis as unknown as { __imageBehavior: string }).__imageBehavior = 'ok'
    vi.stubGlobal('Image', MockImage)
    const onModeChange = vi.fn()
    render(
      <MarsMap>
        <Basemap tileUrl="https://example.test/{z}/{x}/{y}.png" onModeChange={onModeChange} />
      </MarsMap>,
    )
    await waitFor(() => expect(onModeChange).toHaveBeenCalledWith('online'))
  })

  it('manual mode overrides the probe (edge)', async () => {
    ;(globalThis as unknown as { __imageBehavior: string }).__imageBehavior = 'ok'
    vi.stubGlobal('Image', MockImage)
    const onModeChange = vi.fn()
    render(
      <MarsMap>
        <Basemap tileUrl="https://example.test/{z}/{x}/{y}.png" mode="offline" onModeChange={onModeChange} />
      </MarsMap>,
    )
    await waitFor(() => expect(onModeChange).toHaveBeenCalledWith('offline'))
  })

  it('falls back to offline when the probe fails or times out (failure)', async () => {
    ;(globalThis as unknown as { __imageBehavior: string }).__imageBehavior = 'fail'
    vi.stubGlobal('Image', MockImage)
    const onModeChange = vi.fn()
    const { container } = render(
      <MarsMap>
        <Basemap tileUrl="https://example.test/{z}/{x}/{y}.png" onModeChange={onModeChange} />
      </MarsMap>,
    )
    await waitFor(() => expect(onModeChange).toHaveBeenCalledWith('offline'))
    expect(container.querySelector('[data-testid="offline-basemap"]')).toBeTruthy()
  })

  it('stays offline-only when tileUrl is empty (edge)', async () => {
    const onModeChange = vi.fn()
    render(
      <MarsMap>
        <Basemap tileUrl="" onModeChange={onModeChange} />
      </MarsMap>,
    )
    await waitFor(() => expect(onModeChange).toHaveBeenCalledWith('offline'))
  })

  it('offline basemap does not use negative z-index (major)', () => {
    const { container } = render(
      <MarsMap>
        <Basemap tileUrl="" />
      </MarsMap>,
    )
    const offlineEl = container.querySelector('[data-testid="offline-basemap"]')
    expect(offlineEl).toBeTruthy()
    expect(offlineEl?.className).not.toContain('-z-10')
  })

  it('calls the latest onModeChange callback when callback identity changes (major)', async () => {
    ;(globalThis as unknown as { __imageBehavior: string }).__imageBehavior = 'ok'
    vi.stubGlobal('Image', MockImage)
    const initialCallback = vi.fn()
    const updatedCallback = vi.fn()
    const { rerender } = render(
      <MarsMap>
        <Basemap
          tileUrl="https://example.test/{z}/{x}/{y}.png"
          onModeChange={initialCallback}
        />
      </MarsMap>,
    )
    rerender(
      <MarsMap>
        <Basemap
          tileUrl="https://example.test/{z}/{x}/{y}.png"
          onModeChange={updatedCallback}
        />
      </MarsMap>,
    )
    await waitFor(() => expect(updatedCallback).toHaveBeenCalledWith('online'))
    expect(initialCallback).not.toHaveBeenCalled()
  })
})
