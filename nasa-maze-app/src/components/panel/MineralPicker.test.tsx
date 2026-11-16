import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MineralPicker } from './MineralPicker'

describe('MineralPicker', () => {
  it('renders minerals and calls onChange when selecting an available mineral (happy)', () => {
    const onChange = vi.fn()
    render(
      <MineralPicker
        selected="hematita"
        onChange={onChange}
        availableMaterials={['hematita', 'esmectitas', 'tridimita', 'sulfatos']}
      />,
    )

    const select = screen.getByLabelText(/mineral/i)
    expect(select).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /hematite/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /smectites/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /tridymite/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /sulfates/i })).toBeInTheDocument()

    fireEvent.change(select, { target: { value: 'esmectitas' } })
    expect(onChange).toHaveBeenCalledWith('esmectitas')
  })

  it('disables sulfates in fallback mode with tooltip (edge)', () => {
    const onChange = vi.fn()
    render(
      <MineralPicker
        selected="hematita"
        onChange={onChange}
        availableMaterials={['hematita', 'esmectitas', 'tridimita']}
      />,
    )

    const sulfatesOption = screen.getByRole('option', { name: /sulfates/i })
    expect(sulfatesOption).toBeDisabled()
    expect(sulfatesOption).toHaveAttribute('title', 'Requires live routing engine')

    const tooltipElement = screen.getAllByTitle('Requires live routing engine')
    expect(tooltipElement.length).toBeGreaterThanOrEqual(1)
  })

  it('disables entire picker when disabled prop is true (failure/edge)', () => {
    const onChange = vi.fn()
    render(
      <MineralPicker
        selected="hematita"
        onChange={onChange}
        disabled={true}
      />,
    )

    const select = screen.getByLabelText(/mineral/i)
    expect(select).toBeDisabled()
  })
})
