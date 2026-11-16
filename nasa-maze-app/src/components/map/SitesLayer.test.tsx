import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { loadFixture } from '../../test/handlers'
import type { BaseLayersResponse } from '../../api/types'
import { MarsMap } from './MarsMap'
import { SitesLayer } from './SitesLayer'

const layers = loadFixture<BaseLayersResponse>('baseLayers.json')

describe('SitesLayer', () => {
  it('renders chem sites and Bradbury origin (happy)', () => {
    render(
      <MarsMap>
        <SitesLayer layers={layers} material={null} />
      </MarsMap>,
    )
    expect(screen.getAllByTitle('Bradbury Landing').length).toBeGreaterThan(0)
    expect(screen.getAllByTitle('Oudam').length).toBeGreaterThan(0)
  })

  it('highlights candidate sites for the selected mineral (edge)', () => {
    render(
      <MarsMap>
        <SitesLayer layers={layers} material="hematita" />
      </MarsMap>,
    )
    const oudam = screen.getByLabelText('Oudam')
    expect(oudam.getAttribute('style')).toContain('#f97316')
  })

  it('hides the Curiosity traverse when showTraverse is false (failure/edge)', () => {
    const shown = render(
      <MarsMap>
        <SitesLayer layers={layers} material={null} showTraverse />
      </MarsMap>,
    )
    const hidden = render(
      <MarsMap>
        <SitesLayer layers={layers} material={null} showTraverse={false} />
      </MarsMap>,
    )
    expect(shown.container.querySelectorAll('path.leaflet-interactive').length).toBeGreaterThan(0)
    expect(hidden.container.querySelectorAll('path.leaflet-interactive').length).toBe(0)
  })
})
