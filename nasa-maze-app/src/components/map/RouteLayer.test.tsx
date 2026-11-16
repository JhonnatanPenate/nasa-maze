import { act, render, screen } from '@testing-library/react'
import L from 'leaflet'
import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RouteResponse } from '../../api/types'
import { buildRouteView } from '../../domain/routeView'
import { loadFixture } from '../../test/handlers'
import { MarsMap } from './MarsMap'
import { RouteLayer } from './RouteLayer'

const view = () => buildRouteView(structuredClone(loadFixture<RouteResponse>('route.json')))
const allPaths = (c: HTMLElement) => Array.from(c.querySelectorAll('path'))
const strokes = (c: HTMLElement) => allPaths(c).map((p) => p.getAttribute('stroke'))

afterEach(() => vi.restoreAllMocks())

const holder: { map?: L.Map } = {}
function GrabMap() {
  const map = useMap()
  useEffect(() => {
    holder.map = map
  }, [map])
  return null
}

function clickLayer(match: (o: L.PathOptions) => boolean) {
  holder.map!.eachLayer((l) => {
    if (l instanceof L.Polyline && match(l.options)) {
      l.fire('click', { latlng: L.latLng(-4.6, 137.4) })
    }
  })
}

describe('RouteLayer', () => {
  it('draws casing + colored line per segment plus the alternative (happy)', () => {
    const v = view()
    const { container } = render(
      <MarsMap>
        <RouteLayer view={v} colorBy="soil" />
      </MarsMap>,
    )
    expect(strokes(container)).toContain('#4ade80')
    expect(strokes(container).filter((s) => s === '#ffffff')).toHaveLength(v.segments.length)
    expect(container.querySelector('path[stroke-dasharray]')).not.toBeNull()
  })

  it('colors by slope and by risk (edge)', () => {
    const slope = render(
      <MarsMap>
        <RouteLayer view={view()} colorBy="slope" />
      </MarsMap>,
    )
    expect(strokes(slope.container)).not.toContain('#4ade80')
    const risk = render(
      <MarsMap>
        <RouteLayer view={view()} colorBy="risk" />
      </MarsMap>,
    )
    expect(strokes(risk.container).length).toBeGreaterThan(0)
  })

  it('fits bounds to the route (edge)', () => {
    const spy = vi.spyOn(L.Map.prototype, 'fitBounds')
    const v = view()
    render(
      <MarsMap>
        <RouteLayer view={v} colorBy="soil" />
      </MarsMap>,
    )
    const [w, s, e, n] = v.bounds
    expect(spy).toHaveBeenCalledWith([[s, w], [n, e]], expect.anything())
  })

  it('omits the alternative when there is none (failure)', () => {
    const v = { ...view(), alternative: null }
    const { container } = render(
      <MarsMap>
        <RouteLayer view={v} colorBy="soil" />
      </MarsMap>,
    )
    expect(container.querySelector('path[stroke-dasharray]')).toBeNull()
  })

  it('opens a popup with segment info on click (happy)', async () => {
    render(
      <MarsMap>
        <GrabMap />
        <RouteLayer view={view()} colorBy="soil" />
      </MarsMap>,
    )
    act(() => clickLayer((o) => o.color === '#4ade80'))
    expect(await screen.findByText(/Soil: Compact regolith/)).toBeInTheDocument()
  })

  it('selects the alternative when its line is clicked (edge)', () => {
    const onSelect = vi.fn()
    render(
      <MarsMap>
        <GrabMap />
        <RouteLayer view={view()} colorBy="soil" onSelectAlternative={onSelect} />
      </MarsMap>,
    )
    clickLayer((o) => !!o.dashArray)
    expect(onSelect).toHaveBeenCalledWith(true)
  })

  it('draws the selected alternative as a solid bold line (edge)', () => {
    const { container } = render(
      <MarsMap>
        <RouteLayer view={view()} colorBy="soil" alternativeSelected />
      </MarsMap>,
    )
    expect(container.querySelector('path[stroke-dasharray]')).toBeNull()
    expect(strokes(container)).toContain('#38bdf8')
  })
})
