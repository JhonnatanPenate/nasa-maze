import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders a full-screen map container', () => {
    render(<App />)
    const map = screen.getByTestId('map-container')
    expect(map).toBeInTheDocument()
    expect(map).toHaveClass('absolute', 'inset-0')
  })

  it('renders the route panel placeholder', () => {
    render(<App />)
    const panel = screen.getByTestId('route-panel')
    expect(panel).toBeInTheDocument()
    expect(panel).toHaveTextContent(/route/i)
  })

  it('fills the whole viewport', () => {
    render(<App />)
    const map = screen.getByTestId('map-container')
    expect(map.parentElement).toHaveClass('h-screen', 'w-screen')
  })
})
