import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MISSION_DEFAULTS } from '../../domain/mission'
import { MissionSettings } from './MissionSettings'

describe('MissionSettings', () => {
  it('toggles expansion and updates mission params on change (happy)', () => {
    const onChange = vi.fn()
    render(
      <MissionSettings
        mission={MISSION_DEFAULTS}
        onChange={onChange}
        allowedSols={[1360, 2140, 3290, 4710]}
      />,
    )

    const toggleBtn = screen.getByRole('button', { name: /mission settings/i })
    expect(toggleBtn).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(toggleBtn)
    expect(toggleBtn).toHaveAttribute('aria-expanded', 'true')

    const solSelect = screen.getByLabelText(/^sol/i)
    expect(solSelect).toBeInTheDocument()
    fireEvent.change(solSelect, { target: { value: '2140' } })
    expect(onChange).toHaveBeenCalledWith({ ...MISSION_DEFAULTS, sol: 2140 })

    const horaInput = screen.getByLabelText(/start hour/i)
    fireEvent.change(horaInput, { target: { value: '11.5' } })
    expect(onChange).toHaveBeenCalledWith({ ...MISSION_DEFAULTS, hora: 11.5 })

    const vmaxInput = screen.getByLabelText(/max speed/i)
    fireEvent.change(vmaxInput, { target: { value: '800' } })
    expect(onChange).toHaveBeenCalledWith({ ...MISSION_DEFAULTS, vmax: 800 })
  })

  it('renders inputs as disabled in fallback mode (edge - fallback)', () => {
    render(
      <MissionSettings
        mission={MISSION_DEFAULTS}
        onChange={vi.fn()}
        disabled={true}
        defaultExpanded={true}
      />,
    )

    const solSelect = screen.getByLabelText(/^sol/i)
    const horaInput = screen.getByLabelText(/start hour/i)
    const vmaxInput = screen.getByLabelText(/max speed/i)

    expect(solSelect).toBeDisabled()
    expect(horaInput).toBeDisabled()
    expect(vmaxInput).toBeDisabled()
  })

  it('displays validation error messages when present (failure/validation)', () => {
    render(
      <MissionSettings
        mission={{ sol: 9999, hora: 25, vmax: -10 }}
        onChange={vi.fn()}
        defaultExpanded={true}
        errors={{
          sol: 'Sol must be one of the available reference sols',
          hora: 'Start hour must be between 0 and 23.5 in 0.5 h steps',
          vmax: 'Max speed must be a positive number (m/h)',
        }}
      />,
    )

    expect(screen.getByText(/sol must be one of the available/i)).toBeInTheDocument()
    expect(screen.getByText(/start hour must be between/i)).toBeInTheDocument()
    expect(screen.getByText(/max speed must be a positive number/i)).toBeInTheDocument()
  })
})
