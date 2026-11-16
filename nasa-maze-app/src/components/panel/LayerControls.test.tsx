import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LayerControls } from './LayerControls'

describe('LayerControls', () => {
  it('handles layer toggles and selections (happy)', () => {
    const onToggleBasemap = vi.fn()
    const onBandChange = vi.fn()
    const onOpacityChange = vi.fn()
    const onToggleTraverse = vi.fn()
    const onColorByChange = vi.fn()

    render(
      <LayerControls
        basemapOnline={true}
        onToggleBasemap={onToggleBasemap}
        selectedBand="pendiente_grados"
        onBandChange={onBandChange}
        opacity={0.7}
        onOpacityChange={onOpacityChange}
        showTraverse={true}
        onToggleTraverse={onToggleTraverse}
        colorBy="slope"
        onColorByChange={onColorByChange}
        riskAvailable={true}
      />,
    )

    const basemapCheckbox = screen.getByLabelText(/online basemap/i)
    fireEvent.click(basemapCheckbox)
    expect(onToggleBasemap).toHaveBeenCalledWith(false)

    const bandSelect = screen.getByLabelText(/raster band/i)
    fireEvent.change(bandSelect, { target: { value: 'rugosidad_m' } })
    expect(onBandChange).toHaveBeenCalledWith('rugosidad_m')

    const opacitySlider = screen.getByLabelText(/raster opacity/i)
    fireEvent.change(opacitySlider, { target: { value: '0.4' } })
    expect(onOpacityChange).toHaveBeenCalledWith(0.4)

    const traverseCheckbox = screen.getByLabelText(/curiosity traverse/i)
    fireEvent.click(traverseCheckbox)
    expect(onToggleTraverse).toHaveBeenCalledWith(false)

    const soilBtn = screen.getByRole('button', { name: /^soil$/i })
    fireEvent.click(soilBtn)
    expect(onColorByChange).toHaveBeenCalledWith('soil')
  })

  it('hides or disables risk color-by option when risk is not available (edge)', () => {
    render(
      <LayerControls
        basemapOnline={true}
        onToggleBasemap={vi.fn()}
        selectedBand={null}
        onBandChange={vi.fn()}
        opacity={0.7}
        onOpacityChange={vi.fn()}
        showTraverse={true}
        onToggleTraverse={vi.fn()}
        colorBy="soil"
        onColorByChange={vi.fn()}
        riskAvailable={false}
      />,
    )

    const riskBtn = screen.queryByRole('button', { name: /^risk$/i })
    expect(riskBtn).toBeNull()
  })

  it('displays raster error message when provided (failure)', () => {
    render(
      <LayerControls
        basemapOnline={true}
        onToggleBasemap={vi.fn()}
        selectedBand="pendiente_grados"
        onBandChange={vi.fn()}
        opacity={0.7}
        onOpacityChange={vi.fn()}
        showTraverse={true}
        onToggleTraverse={vi.fn()}
        colorBy="slope"
        onColorByChange={vi.fn()}
        rasterError="Raster service returned 502"
      />,
    )

    expect(screen.getByText(/raster service returned 502/i)).toBeInTheDocument()
  })
})
