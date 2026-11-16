import type { HealthResponse, Material } from '../api/types'

export type RoutingMode = 'live' | 'fallback' | 'none'
export type OriginMode = 'free' | 'bradbury' | 'none'

export interface Capabilities {
  routing: RoutingMode
  originMode: OriginMode
  materials: Material[]
  missionEditable: boolean
  searchEnabled: boolean
  riskEnabled: boolean
}

const ALL_MATERIALS: Material[] = ['hematita', 'esmectitas', 'tridimita', 'sulfatos']
const FALLBACK_MATERIALS: Material[] = ['hematita', 'esmectitas', 'tridimita']

export function capabilitiesFromHealth(health: HealthResponse): Capabilities {
  if (health.servicios.ms6 === 'ok') {
    return {
      routing: 'live',
      originMode: 'free',
      materials: [...ALL_MATERIALS],
      missionEditable: true,
      searchEnabled: health.servicios.ms1 === 'ok',
      riskEnabled: health.servicios.ms5 === 'ok',
    }
  }
  if (health.fallback_precalculado) {
    return {
      routing: 'fallback',
      originMode: 'bradbury',
      materials: [...FALLBACK_MATERIALS],
      missionEditable: false,
      searchEnabled: false,
      riskEnabled: false,
    }
  }
  return {
    routing: 'none',
    originMode: 'none',
    materials: [],
    missionEditable: false,
    searchEnabled: false,
    riskEnabled: false,
  }
}
