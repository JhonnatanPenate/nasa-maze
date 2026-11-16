import { describe, expect, it } from 'vitest'
import type { HealthResponse } from '../api/types'
import { loadFixture } from '../test/handlers'
import {
  buildRouteRequest,
  isInsideAoi,
  MISSION_DEFAULTS,
  validateMission,
  type MissionParams,
} from './mission'

const health = () => loadFixture<HealthResponse>('health.live.json')
const SOLS = [1360, 2140, 3290, 4710]
const valid: MissionParams = { sol: 1360, hora: 9, vmax: 1000 }

describe('MISSION_DEFAULTS', () => {
  it('match the reference request (sol 1360, hora 9, vmax 1000)', () => {
    expect(MISSION_DEFAULTS).toEqual({ sol: 1360, hora: 9, vmax: 1000 })
    expect(validateMission(MISSION_DEFAULTS, SOLS)).toEqual({})
  })
})

describe('isInsideAoi', () => {
  const aoi = health().aoi

  it('accepts a point inside the AOI', () => {
    expect(isInsideAoi(137.44, -4.59, aoi)).toBe(true)
  })

  it('includes the boundary', () => {
    expect(isInsideAoi(137.345, -4.74, aoi)).toBe(true)
    expect(isInsideAoi(137.455, -4.58, aoi)).toBe(true)
  })

  it('rejects points outside the AOI', () => {
    expect(isInsideAoi(137.5, -4.59, aoi)).toBe(false)
    expect(isInsideAoi(137.44, -4.8, aoi)).toBe(false)
  })
})

describe('validateMission', () => {
  it('accepts a valid mission', () => {
    expect(validateMission(valid, SOLS)).toEqual({})
  })

  it('accepts hour 23.5 and rejects 24', () => {
    expect(validateMission({ ...valid, hora: 23.5 }, SOLS).hora).toBeUndefined()
    expect(validateMission({ ...valid, hora: 24 }, SOLS).hora).toBeTypeOf('string')
    expect(validateMission({ ...valid, hora: -0.5 }, SOLS).hora).toBeTypeOf('string')
    expect(validateMission({ ...valid, hora: 9.25 }, SOLS).hora).toBeTypeOf('string')
  })

  it('rejects a sol not offered by health.sols', () => {
    expect(validateMission({ ...valid, sol: 999 }, SOLS).sol).toBeTypeOf('string')
  })

  it('rejects non-positive vmax', () => {
    expect(validateMission({ ...valid, vmax: 0 }, SOLS).vmax).toBeTypeOf('string')
    expect(validateMission({ ...valid, vmax: -10 }, SOLS).vmax).toBeTypeOf('string')
  })
})

describe('buildRouteRequest', () => {
  it('builds the exact POST /api/ruta body', () => {
    const req = buildRouteRequest({ lon: 137.4416, lat: -4.5895 }, 'hematita', valid)
    expect(req).toEqual({
      lon: 137.4416,
      lat: -4.5895,
      material: 'hematita',
      sol: 1360,
      hora: 9,
      vmax: 1000,
    })
  })
})
