import type { Material, RouteRequest } from '../api/types'

export interface MissionParams {
  sol: number
  hora: number
  vmax: number
}

export interface MissionErrors {
  sol?: string
  hora?: string
  vmax?: string
}

export const MISSION_DEFAULTS: MissionParams = { sol: 1360, hora: 9, vmax: 1000 }

export const HORA_MIN = 0
export const HORA_MAX = 23.5
export const HORA_STEP = 0.5

export const BRADBURY = { lon: 137.4416, lat: -4.5895, nombre: 'Bradbury Landing' } as const

export function isInsideAoi(
  lon: number,
  lat: number,
  aoi: readonly [number, number, number, number],
): boolean {
  const [w, s, e, n] = aoi
  return lon >= w && lon <= e && lat >= s && lat <= n
}

export function validateMission(mission: MissionParams, allowedSols: number[]): MissionErrors {
  const errors: MissionErrors = {}
  if (!allowedSols.includes(mission.sol)) {
    errors.sol = 'Sol must be one of the available reference sols'
  }
  const { hora } = mission
  if (
    !Number.isFinite(hora) ||
    hora < HORA_MIN ||
    hora > HORA_MAX ||
    Math.abs(hora / HORA_STEP - Math.round(hora / HORA_STEP)) > 1e-9
  ) {
    errors.hora = `Start hour must be between ${HORA_MIN} and ${HORA_MAX} in ${HORA_STEP} h steps`
  }
  if (!Number.isFinite(mission.vmax) || mission.vmax <= 0) {
    errors.vmax = 'Max speed must be a positive number (m/h)'
  }
  return errors
}

export function buildRouteRequest(
  origin: { lon: number; lat: number },
  material: Material,
  mission: MissionParams,
): RouteRequest {
  return {
    lon: origin.lon,
    lat: origin.lat,
    material,
    sol: mission.sol,
    hora: mission.hora,
    vmax: mission.vmax,
  }
}
