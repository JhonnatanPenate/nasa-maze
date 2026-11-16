import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import type { HealthResponse } from '../../api/types'
import { capabilitiesFromHealth } from '../../domain/capabilities'
import { BRADBURY } from '../../domain/mission'
import type { NamedPoint } from '../../domain/sites'
import { loadFixture } from '../../test/handlers'
import { server } from '../../test/server'
import { RoutePanel } from './RoutePanel'

const liveHealth = loadFixture<HealthResponse>('health.live.json')
const fallbackHealth = loadFixture<HealthResponse>('health.fallback.json')
const noneHealth = loadFixture<HealthResponse>('health.none.json')

const liveCapabilities = capabilitiesFromHealth(liveHealth)
const fallbackCapabilities = capabilitiesFromHealth(fallbackHealth)
const noneCapabilities = capabilitiesFromHealth(noneHealth)

const sampleOptions: NamedPoint[] = [
  { nombre: BRADBURY.nombre, lon: BRADBURY.lon, lat: BRADBURY.lat },
  { nombre: 'Oudam', lon: 137.401, lat: -4.621 },
]

describe('RoutePanel', () => {
  it('selects mineral and sends correct POST body on Find route (happy)', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/ruta', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(loadFixture('route.json'))
      }),
    )

    const onRouteCalculated = vi.fn()
    render(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
        onRouteCalculated={onRouteCalculated}
      />,
    )

    // Select mineral
    const mineralSelect = screen.getByLabelText(/mineral/i)
    fireEvent.change(mineralSelect, { target: { value: 'esmectitas' } })

    // Find route button
    const findBtn = screen.getByRole('button', { name: /find route/i })
    fireEvent.click(findBtn)

    await waitFor(() => {
      expect(onRouteCalculated).toHaveBeenCalled()
    })

    expect(capturedBody).toEqual({
      lon: BRADBURY.lon,
      lat: BRADBURY.lat,
      material: 'esmectitas',
      sol: 1360,
      hora: 9,
      vmax: 1000,
    })
  })

  it('updates origin via map click prop and sends updated coordinates (edge - map click)', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/ruta', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(loadFixture('route.json'))
      }),
    )

    const onOriginChange = vi.fn()
    const { rerender } = render(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
        selectedOrigin={{ lon: BRADBURY.lon, lat: BRADBURY.lat, nombre: BRADBURY.nombre }}
        onOriginChange={onOriginChange}
      />,
    )

    // Simulate origin change from map click
    rerender(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
        selectedOrigin={{
          lon: 137.39,
          lat: -4.65,
          nombre: 'Map point (137.3900, -4.6500)',
        }}
        onOriginChange={onOriginChange}
      />,
    )

    const findBtn = screen.getByRole('button', { name: /find route/i })
    fireEvent.click(findBtn)

    await waitFor(() => {
      expect(capturedBody).not.toBeNull()
    })

    expect(capturedBody).toMatchObject({
      lon: 137.39,
      lat: -4.65,
      material: 'hematita',
    })
  })

  it('sets origin via place search and sends found coordinates (edge - search)', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/ruta', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(loadFixture('route.json'))
      }),
    )

    render(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
      />,
    )

    const searchInput = screen.getByLabelText(/search origin place/i)
    fireEvent.change(searchInput, { target: { value: 'Glen Etive' } })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    const resultBtn = await screen.findByRole('button', { name: /Glen Etive/i })
    fireEvent.click(resultBtn)

    const findBtn = screen.getByRole('button', { name: /find route/i })
    fireEvent.click(findBtn)

    await waitFor(() => {
      expect(capturedBody).not.toBeNull()
    })

    expect(capturedBody).toMatchObject({
      lon: 137.3835,
      lat: -4.7303,
      material: 'hematita',
    })
  })

  it('allows canceling an in-flight route search (edge - cancel)', async () => {
    server.use(
      http.post('/api/ruta', async () => {
        await new Promise((r) => setTimeout(r, 200))
        return HttpResponse.json(loadFixture('route.json'))
      }),
    )

    render(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /find route/i }))

    const cancelBtn = await screen.findByRole('button', { name: /cancel/i })
    expect(cancelBtn).toBeInTheDocument()

    fireEvent.click(cancelBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /find route/i })).toBeInTheDocument()
    })
  })

  it('disables sulfates with tooltip and locks settings in fallback mode (failure/fallback)', () => {
    render(
      <RoutePanel
        health={fallbackHealth}
        capabilities={fallbackCapabilities}
        originOptions={sampleOptions}
      />,
    )

    // Sulfates disabled with tooltip
    const sulfatesOption = screen.getByRole('option', { name: /sulfates/i })
    expect(sulfatesOption).toBeDisabled()
    expect(sulfatesOption).toHaveAttribute('title', 'Requires live routing engine')

    // Origin locked
    expect(screen.getByText(/locked to bradbury/i)).toBeInTheDocument()

    // Mission settings inputs rendered but disabled (read-only)
    fireEvent.click(screen.getByRole('button', { name: /mission settings/i }))
    expect(screen.getByLabelText(/^sol/i)).toBeDisabled()
    expect(screen.getByLabelText(/start hour/i)).toBeDisabled()
    expect(screen.getByLabelText(/max speed/i)).toBeDisabled()
  })

  it('shows error detail for 503 and refetches health (failure - 503)', async () => {
    const onRefetchHealth = vi.fn()
    server.use(
      http.post('/api/ruta', () => {
        return HttpResponse.json({ detail: 'MS6 routing service unavailable' }, { status: 503 })
      }),
    )

    render(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
        onRefetchHealth={onRefetchHealth}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /find route/i }))

    const errorAlert = await screen.findByRole('alert')
    expect(errorAlert).toHaveTextContent('MS6 routing service unavailable')
    expect(onRefetchHealth).toHaveBeenCalledTimes(1)
  })

  it('shows error detail for 400 (failure - 400)', async () => {
    server.use(
      http.post('/api/ruta', () => {
        return HttpResponse.json({ detail: 'Origin is outside the AOI' }, { status: 400 })
      }),
    )

    render(
      <RoutePanel
        health={liveHealth}
        capabilities={liveCapabilities}
        originOptions={sampleOptions}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /find route/i }))

    const errorAlert = await screen.findByRole('alert')
    expect(errorAlert).toHaveTextContent('Origin is outside the AOI')
  })

  it('disables find route button when routing is unavailable (failure - none)', () => {
    render(
      <RoutePanel
        health={noneHealth}
        capabilities={noneCapabilities}
        originOptions={sampleOptions}
      />,
    )

    const findBtn = screen.getByRole('button', { name: /find route/i })
    expect(findBtn).toBeDisabled()
    expect(screen.getByText(/routing engine unavailable/i)).toBeInTheDocument()
  })
})
