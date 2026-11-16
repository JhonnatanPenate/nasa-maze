import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders live routing and online basemap badges (happy)', () => {
    render(<StatusBadge routingMode="live" basemapOnline={true} />)

    expect(screen.getByText(/Routing: Live/i)).toBeInTheDocument()
    expect(screen.getByText(/Basemap: Online/i)).toBeInTheDocument()
  })

  it('renders fallback routing and offline basemap badges (edge)', () => {
    render(<StatusBadge routingMode="fallback" basemapOnline={false} />)

    expect(screen.getByText(/Routing: Fallback/i)).toBeInTheDocument()
    expect(screen.getByText(/Basemap: Offline/i)).toBeInTheDocument()
  })

  it('renders unavailable routing badge when mode is none (failure)', () => {
    render(<StatusBadge routingMode="none" basemapOnline={true} />)

    expect(screen.getByText(/Routing: Unavailable/i)).toBeInTheDocument()
  })
})
