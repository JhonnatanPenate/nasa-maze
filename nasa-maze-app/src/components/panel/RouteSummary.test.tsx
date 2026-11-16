import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { RouteResponse } from '../../api/types'
import { buildRouteView } from '../../domain/routeView'
import { loadFixture } from '../../test/handlers'
import { RouteSummary } from './RouteSummary'

const view = () => buildRouteView(structuredClone(loadFixture<RouteResponse>('route.json')))

describe('RouteSummary', () => {
  it('shows KPIs, source and risk badges (happy)', () => {
    render(<RouteSummary view={view()} onNewRoute={() => {}} />)
    expect(screen.getByText(/7\.73/)).toBeInTheDocument()
    expect(screen.getByText('S+1 08:15')).toBeInTheDocument()
    expect(screen.getByText('Live')).toBeInTheDocument()
    expect(screen.getByText(/Risk: Medium/)).toBeInTheDocument()
    expect(screen.getByText(/Oudam/)).toBeInTheDocument()
  })

  it('hides the risk badge when there is no riesgo and lists derived warnings (edge)', () => {
    const v = { ...view(), riskLevel: null, overallRisk: null, warnings: ['Route includes a night wait'] }
    render(<RouteSummary view={v} onNewRoute={() => {}} />)
    expect(screen.queryByText(/Risk:/)).toBeNull()
    expect(screen.getByText('Route includes a night wait')).toBeInTheDocument()
  })

  it('omits the Bagnold comparison when absent and fires New route (failure)', () => {
    const onNew = vi.fn()
    const v = view()
    v.kpis.comparativa = null
    render(<RouteSummary view={v} onNewRoute={onNew} />)
    expect(screen.queryByText(/Bagnold/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /new route/i }))
    expect(onNew).toHaveBeenCalled()
  })

  it('shows the Bagnold comparison and selects the alternative (edge)', () => {
    const onSelect = vi.fn()
    render(<RouteSummary view={view()} onNewRoute={() => {}} showAlternative={false} onToggleAlternative={onSelect} />)
    expect(screen.getByText(/Bagnold/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /compare alternative/i }))
    expect(onSelect).toHaveBeenCalledWith(true)
  })
})
