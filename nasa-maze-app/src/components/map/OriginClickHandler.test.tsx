import { act, render } from '@testing-library/react'
import type { Map as LeafletMap } from 'leaflet'
import { MapContainer, useMap } from 'react-leaflet'
import { describe, expect, it, vi } from 'vitest'
import { OriginClickHandler } from './OriginClickHandler'

describe('OriginClickHandler', () => {
  const AOI = [137.345, -4.74, 137.455, -4.58] as const

  it('selects origin on map click inside AOI when enabled (happy)', () => {
    let mapInstance: LeafletMap | null = null
    function Capture() {
      mapInstance = useMap()
      return null
    }

    const onSelectOrigin = vi.fn()
    render(
      <MapContainer center={[-4.6, 137.4]} zoom={11}>
        <OriginClickHandler enabled={true} aoi={AOI} onSelectOrigin={onSelectOrigin} />
        <Capture />
      </MapContainer>,
    )

    expect(mapInstance).not.toBeNull()
    act(() => {
      mapInstance!.fire('click', { latlng: { lat: -4.65, lng: 137.4 } })
    })

    expect(onSelectOrigin).toHaveBeenCalledTimes(1)
    expect(onSelectOrigin).toHaveBeenCalledWith({
      lon: 137.4,
      lat: -4.65,
      nombre: 'Map point (137.4000, -4.6500)',
    })
  })

  it('rejects click outside AOI (edge)', () => {
    let mapInstance: LeafletMap | null = null
    function Capture() {
      mapInstance = useMap()
      return null
    }

    const onSelectOrigin = vi.fn()
    render(
      <MapContainer center={[-4.6, 137.4]} zoom={11}>
        <OriginClickHandler enabled={true} aoi={AOI} onSelectOrigin={onSelectOrigin} />
        <Capture />
      </MapContainer>,
    )

    act(() => {
      mapInstance!.fire('click', { latlng: { lat: 0.0, lng: 0.0 } })
    })

    expect(onSelectOrigin).not.toHaveBeenCalled()
  })

  it('ignores clicks when enabled is false (failure/disabled)', () => {
    let mapInstance: LeafletMap | null = null
    function Capture() {
      mapInstance = useMap()
      return null
    }

    const onSelectOrigin = vi.fn()
    render(
      <MapContainer center={[-4.6, 137.4]} zoom={11}>
        <OriginClickHandler enabled={false} aoi={AOI} onSelectOrigin={onSelectOrigin} />
        <Capture />
      </MapContainer>,
    )

    act(() => {
      mapInstance!.fire('click', { latlng: { lat: -4.65, lng: 137.4 } })
    })

    expect(onSelectOrigin).not.toHaveBeenCalled()
  })
})
