import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BRADBURY } from '../../domain/mission'
import type { NamedPoint } from '../../domain/sites'
import { OriginPicker } from './OriginPicker'

const SAMPLE_OPTIONS: NamedPoint[] = [
  { nombre: BRADBURY.nombre, lon: BRADBURY.lon, lat: BRADBURY.lat },
  { nombre: 'Oudam', lon: 137.401, lat: -4.621 },
  { nombre: 'John Klein', lon: 137.442, lat: -4.591 },
]

describe('OriginPicker', () => {
  it('selects origin from options dropdown (happy)', () => {
    const onChange = vi.fn()
    render(
      <OriginPicker
        value={SAMPLE_OPTIONS[0]}
        onChange={onChange}
        options={SAMPLE_OPTIONS}
        originMode="free"
      />,
    )

    const select = screen.getByLabelText(/origin/i)
    expect(select).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Bradbury Landing/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Oudam/i })).toBeInTheDocument()

    fireEvent.change(select, { target: { value: '137.401,-4.621' } })
    expect(onChange).toHaveBeenCalledWith(SAMPLE_OPTIONS[1])
  })

  it('searches places and selects origin from search result (edge - search)', async () => {
    const onChange = vi.fn()
    render(
      <OriginPicker
        value={SAMPLE_OPTIONS[0]}
        onChange={onChange}
        options={SAMPLE_OPTIONS}
        originMode="free"
        searchEnabled={true}
      />,
    )

    const searchInput = screen.getByLabelText(/search origin place/i)
    expect(searchInput).toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: 'Glen Etive' } })
    const searchBtn = screen.getByRole('button', { name: /search/i })
    fireEvent.click(searchBtn)

    const resultBtn = await screen.findByRole('button', { name: /Glen Etive/i })
    expect(resultBtn).toBeInTheDocument()

    fireEvent.click(resultBtn)
    expect(onChange).toHaveBeenCalledWith({
      nombre: 'Glen Etive',
      lon: 137.3835,
      lat: -4.7303,
    })
  })

  it('displays custom origin set from map click (edge - map click)', () => {
    const customOrigin = {
      nombre: 'Map point (137.3900, -4.6100)',
      lon: 137.39,
      lat: -4.61,
    }
    render(
      <OriginPicker
        value={customOrigin}
        onChange={vi.fn()}
        options={SAMPLE_OPTIONS}
        originMode="free"
      />,
    )

    expect(screen.getByText(/Map point \(137.3900, -4.6100\)/i)).toBeInTheDocument()
  })

  it('locks origin to Bradbury in fallback mode (failure/fallback)', () => {
    const onChange = vi.fn()
    render(
      <OriginPicker
        value={SAMPLE_OPTIONS[0]}
        onChange={onChange}
        options={SAMPLE_OPTIONS}
        originMode="bradbury"
        searchEnabled={true}
      />,
    )

    const select = screen.getByLabelText(/origin/i)
    expect(select).toBeDisabled()
    expect(screen.queryByLabelText(/search origin place/i)).not.toBeInTheDocument()
    expect(screen.getByText(/locked to bradbury/i)).toBeInTheDocument()
  })
})
