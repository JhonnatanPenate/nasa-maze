import { describe, expect, it } from 'vitest'
import type { HealthResponse } from '../api/types'
import { loadFixture } from '../test/handlers'
import { capabilitiesFromHealth } from './capabilities'

const live = () => structuredClone(loadFixture<HealthResponse>('health.live.json'))
const fallback = () => loadFixture<HealthResponse>('health.fallback.json')
const none = () => loadFixture<HealthResponse>('health.none.json')

describe('capabilitiesFromHealth', () => {
  it('enables live routing with all materials and editable mission when ms6 is ok', () => {
    const caps = capabilitiesFromHealth(live())
    expect(caps.routing).toBe('live')
    expect(caps.originMode).toBe('free')
    expect(caps.materials).toEqual(['hematita', 'esmectitas', 'tridimita', 'sulfatos'])
    expect(caps.missionEditable).toBe(true)
  })

  it('toggles search on ms1 and risk on ms5 independently', () => {
    const noMs1 = live()
    noMs1.servicios.ms1 = 'down'
    expect(capabilitiesFromHealth(noMs1).searchEnabled).toBe(false)
    expect(capabilitiesFromHealth(live()).searchEnabled).toBe(true)

    const noMs5 = live()
    noMs5.servicios.ms5 = 'down'
    expect(capabilitiesFromHealth(noMs5).riskEnabled).toBe(false)
    expect(capabilitiesFromHealth(live()).riskEnabled).toBe(true)
    expect(capabilitiesFromHealth(noMs5).routing).toBe('live')
  })

  it('locks to Bradbury, three minerals and a frozen mission in fallback mode', () => {
    const caps = capabilitiesFromHealth(fallback())
    expect(caps.routing).toBe('fallback')
    expect(caps.originMode).toBe('bradbury')
    expect(caps.materials).toEqual(['hematita', 'esmectitas', 'tridimita'])
    expect(caps.missionEditable).toBe(false)
    expect(caps.searchEnabled).toBe(false)
    expect(caps.riskEnabled).toBe(false)
  })

  it('reports no routing when ms6 is down and there is no precalculated fallback', () => {
    const caps = capabilitiesFromHealth(none())
    expect(caps.routing).toBe('none')
    expect(caps.originMode).toBe('none')
    expect(caps.materials).toEqual([])
    expect(caps.missionEditable).toBe(false)
    expect(caps.searchEnabled).toBe(false)
  })

  it('treats no_configurado the same as down for ms6', () => {
    const health = live()
    health.servicios.ms6 = 'no_configurado'
    expect(capabilitiesFromHealth(health).routing).toBe('fallback')
  })
})
