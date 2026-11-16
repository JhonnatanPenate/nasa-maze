import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarsMap } from './MarsMap'

describe('MarsMap', () => {
  it('renders a leaflet container (happy)', () => {
    render(<MarsMap />)
    expect(screen.getByTestId('mars-map').querySelector('.leaflet-container')).toBeTruthy()
  })

  it('renders children passed into the map (edge)', () => {
    render(
      <MarsMap>
        <div data-testid="child-layer" />
      </MarsMap>,
    )
    expect(screen.getByTestId('child-layer')).toBeInTheDocument()
  })

  it('renders without children without crashing (failure-ish: missing optional prop)', () => {
    expect(() => render(<MarsMap />)).not.toThrow()
  })

  it('creates an isolated stacking context (major)', () => {
    render(<MarsMap />)
    const mapWrapper = screen.getByTestId('mars-map')
    expect(mapWrapper.className).toContain('isolate')
  })
})
