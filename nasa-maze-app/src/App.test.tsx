import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpResponse, http } from 'msw'
import type { RouteResponse } from './api/types'
import App from './App'
import { buildRouteView, slopeColor } from './domain/routeView'
import { loadFixture } from './test/handlers'
import { server } from './test/server'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders a full-screen map container and MarsMap shell', () => {
    render(<App />)
    const map = screen.getByTestId('map-container')
    expect(map).toBeInTheDocument()
    expect(map).toHaveClass('absolute', 'inset-0')
    expect(screen.getByTestId('mars-map')).toBeInTheDocument()
  })

  it('renders the RoutePanel, StatusBadge, LayerControls and Legend', async () => {
    render(<App />)
    expect(screen.getByTestId('route-panel')).toBeInTheDocument()
    expect(screen.getByTestId('status-badges')).toBeInTheDocument()
    expect(screen.getByTestId('layer-controls')).toBeInTheDocument()
    expect(screen.getByTestId('map-legend')).toBeInTheDocument()

    // Health and base layers load from MSW fixtures
    await waitFor(() => {
      expect(screen.getByText(/routing: live/i)).toBeInTheDocument()
    })
  })

  it('shows the offline basemap status when the tile probe fails', async () => {
    class FailedImage {
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      set src(_value: string) {
        queueMicrotask(() => this.onerror?.())
      }
    }
    vi.stubGlobal('Image', FailedImage)

    render(<App />)

    expect(await screen.findByText('Basemap: Offline')).toBeInTheDocument()
  })

  it('fills the whole viewport', () => {
    render(<App />)
    const map = screen.getByTestId('map-container')
    expect(map.parentElement).toHaveClass('h-screen', 'w-screen')
  })

  it('shows the route summary after finding a route and returns on New route', async () => {
    render(<App />)
    const find = await screen.findByRole('button', { name: /find route/i })
    await waitFor(() => expect(find).toBeEnabled())
    fireEvent.click(find)
    expect(await screen.findByTestId('route-summary')).toBeInTheDocument()
    expect(screen.getByTestId('route-panel').parentElement).toHaveClass('hidden')
    fireEvent.click(screen.getByRole('button', { name: /new route/i }))
    expect(screen.getByTestId('route-panel').parentElement).not.toHaveClass('hidden')
    expect(screen.queryByTestId('route-summary')).toBeNull()
  })

  it('falls back to slope colors when Risk mode is chosen but the route has no riesgo', async () => {
    const res = { ...structuredClone(loadFixture<RouteResponse>('route.json')), riesgo: null }
    server.use(http.post('/api/ruta', () => HttpResponse.json(res)))
    const { container } = render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /^risk$/i }))
    const find = screen.getByRole('button', { name: /find route/i })
    await waitFor(() => expect(find).toBeEnabled())
    fireEvent.click(find)
    await screen.findByTestId('route-summary')
    const slope = slopeColor(buildRouteView(res).segments[0].inclinacion_grados)
    await waitFor(() => expect(container.querySelector(`path[stroke="${slope}"]`)).not.toBeNull())
  })
})
