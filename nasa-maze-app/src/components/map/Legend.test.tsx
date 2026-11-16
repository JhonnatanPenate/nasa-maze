import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Legend } from './Legend'

describe('Legend', () => {
  it('renders the slope scale (happy)', () => {
    render(<Legend mode="slope" />)
    expect(screen.getByText('< 5°')).toBeInTheDocument()
    expect(screen.getByText('≥ 15°')).toBeInTheDocument()
  })

  it('renders soil types for soil mode (edge)', () => {
    render(<Legend mode="soil" soilTypes={['arena_dunas']} />)
    expect(screen.getByText('Dune sand')).toBeInTheDocument()
  })

  it('renders risk levels including unknown (failure/edge case)', () => {
    render(<Legend mode="risk" />)
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })
})
