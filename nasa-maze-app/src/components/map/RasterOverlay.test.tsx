import { render, waitFor } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../../test/server'
import { MarsMap } from './MarsMap'
import { RasterOverlay } from './RasterOverlay'

describe('RasterOverlay', () => {
  it('draws the overlay using the X-Bounds header (happy)', async () => {
    const { container } = render(
      <MarsMap>
        <RasterOverlay banda="pendiente_grados" />
      </MarsMap>,
    )
    await waitFor(() =>
      expect(container.querySelector('.leaflet-image-layer')).toBeTruthy(),
    )
  })

  it('renders nothing while no band is selected (edge)', () => {
    const { container } = render(
      <MarsMap>
        <RasterOverlay banda={null} />
      </MarsMap>,
    )
    expect(container.querySelector('.leaflet-image-layer')).toBeFalsy()
  })

  it('reports an error and keeps the map on a 502 (failure)', async () => {
    server.use(
      http.get('/api/capas/raster/:banda', () =>
        HttpResponse.json({ detail: 'raster unreadable' }, { status: 502 }),
      ),
    )
    const onError = vi.fn()
    const { container } = render(
      <MarsMap>
        <RasterOverlay banda="pendiente_grados" onError={onError} />
      </MarsMap>,
    )
    await waitFor(() => expect(onError).toHaveBeenCalledWith(expect.any(String)))
    expect(container.querySelector('.leaflet-container')).toBeTruthy()
    expect(container.querySelector('.leaflet-image-layer')).toBeFalsy()
  })

  it('calls latest onError callback when callback reference changes (major)', async () => {
    server.use(
      http.get('/api/capas/raster/:banda', () =>
        HttpResponse.json({ detail: 'raster unreadable' }, { status: 502 }),
      ),
    )
    const initialOnError = vi.fn()
    const updatedOnError = vi.fn()
    const { rerender } = render(
      <MarsMap>
        <RasterOverlay banda="pendiente_grados" onError={initialOnError} />
      </MarsMap>,
    )
    rerender(
      <MarsMap>
        <RasterOverlay banda="pendiente_grados" onError={updatedOnError} />
      </MarsMap>,
    )
    await waitFor(() => expect(updatedOnError).toHaveBeenCalledWith(expect.any(String)))
    expect(initialOnError).not.toHaveBeenCalledWith(expect.any(String))
  })
})
