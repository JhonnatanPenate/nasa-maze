import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

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

  it('fills the whole viewport', () => {
    render(<App />)
    const map = screen.getByTestId('map-container')
    expect(map.parentElement).toHaveClass('h-screen', 'w-screen')
  })
})
