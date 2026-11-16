import type {
  ComparativaBagnold,
  RouteFeature,
  RouteResponse,
  RouteSource,
} from '../api/types'
import { riskLevelColor } from './labels'
import type { NamedPoint } from './sites'

export class RouteViewError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'RouteViewError'
  }
}

export interface RouteSegmentView {
  coordinates: [number, number][]
  tipo_suelo: string
  modelo_usado: string
  inclinacion_grados: number
}

export interface AlternativeRoute {
  nombre: string
  coordinates: [number, number][]
}

export interface RiskSegmentView {
  from: [number, number]
  to: [number, number]
  distance_m: number
  risk: number | null
  warnings: string[]
  blocking: boolean
}

export interface RouteKpis {
  distanciaKm: number
  horaLlegada: string
  dosisRadAcumUgy: number
  horasEsperaNocturna: number
  objetivo: string
  material: string
  fuente: RouteSource
  comparativa: ComparativaBagnold | null
}

export interface RouteView {
  segments: RouteSegmentView[]
  alternative: AlternativeRoute | null
  target: (NamedPoint & { material: string }) | null
  origin: NamedPoint | null
  bounds: [number, number, number, number]
  kpis: RouteKpis
  riskSegments: RiskSegmentView[]
  riskLevel: string | null
  overallRisk: number | null
  warnings: string[]
  coveragePct: number | null
}

function lineCoords(geometry: { type?: string; coordinates?: unknown } | null): [number, number][] {
  if (
    !geometry ||
    geometry.type !== 'LineString' ||
    !Array.isArray(geometry.coordinates) ||
    geometry.coordinates.length === 0 ||
    !geometry.coordinates.every(
      (c) => Array.isArray(c) && c.length >= 2 && Number.isFinite(c[0]) && Number.isFinite(c[1]),
    )
  ) {
    throw new RouteViewError('Route feature has a malformed LineString geometry')
  }
  return geometry.coordinates.map((c) => [c[0], c[1]] as [number, number])
}

function pointCoords(geometry: { type?: string; coordinates?: unknown } | null): [number, number] {
  const c = geometry?.coordinates
  if (
    !geometry ||
    geometry.type !== 'Point' ||
    !Array.isArray(c) ||
    c.length < 2 ||
    !Number.isFinite(c[0]) ||
    !Number.isFinite(c[1])
  ) {
    throw new RouteViewError('Route feature has a malformed Point geometry')
  }
  return [c[0], c[1]]
}

function derivedWarnings(res: RouteResponse): string[] {
  const warnings: string[] = []
  const maxSlope = (res.tramos ?? []).reduce(
    (max, t) => Math.max(max, typeof t?.inclinacion_max_grados === 'number' ? t.inclinacion_max_grados : -Infinity),
    -Infinity,
  )
  if (maxSlope >= 15) warnings.push('Route crosses slopes of 15° or more')
  const dunes = res.resumen?.comparativa_bagnold?.celdas_duna_ruta_optima ?? 0
  if (dunes > 0) warnings.push('Route crosses dune cells')
  const nightWait = res.resumen?.horas_espera_nocturna ?? 0
  if (nightWait > 0) warnings.push('Route includes a night wait')
  return warnings
}

function riskWarnings(res: RouteResponse): string[] {
  const riesgo = res.riesgo
  if (!riesgo) return []
  const warnings = [...(riesgo.warnings_summary ?? [])]
  for (const r of riesgo.restrictions ?? []) {
    if (r.blocking && !warnings.includes(r.message)) warnings.push(r.message)
  }
  return warnings
}

export function buildRouteView(res: RouteResponse): RouteView {
  const geojson = res?.geojson
  if (!geojson || geojson.type !== 'FeatureCollection' || !Array.isArray(geojson.features)) {
    throw new RouteViewError('Route response contains no valid FeatureCollection')
  }

  const segments: RouteSegmentView[] = []
  let alternative: AlternativeRoute | null = null
  let target: RouteView['target'] = null
  let origin: NamedPoint | null = null
  let w = Infinity
  let s = Infinity
  let e = -Infinity
  let n = -Infinity
  const extend = (lon: number, lat: number) => {
    w = Math.min(w, lon)
    s = Math.min(s, lat)
    e = Math.max(e, lon)
    n = Math.max(n, lat)
  }

  for (const feature of geojson.features as RouteFeature[]) {
    const capa = feature?.properties?.capa
    if (capa === 'ruta_optima') {
      const coordinates = lineCoords(feature.geometry)
      segments.push({
        coordinates,
        tipo_suelo: feature.properties.tipo_suelo,
        modelo_usado: feature.properties.modelo_usado,
        inclinacion_grados: feature.properties.inclinacion_grados,
      })
      for (const [lon, lat] of coordinates) extend(lon, lat)
    } else if (capa === 'contrafactual') {
      const coordinates = lineCoords(feature.geometry)
      alternative = { nombre: feature.properties.nombre ?? 'contrafactual', coordinates }
      for (const [lon, lat] of coordinates) extend(lon, lat)
    } else if (capa === 'objetivo') {
      const [lon, lat] = pointCoords(feature.geometry)
      target = { nombre: feature.properties.nombre, material: feature.properties.material, lon, lat }
      extend(lon, lat)
    } else if (capa === 'origen') {
      const [lon, lat] = pointCoords(feature.geometry)
      origin = { nombre: feature.properties.nombre, lon, lat }
      extend(lon, lat)
    }
  }

  if (segments.length === 0) {
    throw new RouteViewError('Route response contains no optimal route segments')
  }

  const riesgo = res.riesgo
  const blocking = new Set<number>([
    ...(riesgo?.blocking_segments ?? []),
    ...(riesgo?.restrictions ?? []).filter((r) => r.blocking).map((r) => r.segment),
  ])

  return {
    segments,
    alternative,
    target,
    origin,
    bounds: [w, s, e, n],
    kpis: {
      distanciaKm: res.resumen.distancia_km,
      horaLlegada: res.resumen.hora_llegada,
      dosisRadAcumUgy: res.resumen.dosis_rad_acum_uGy,
      horasEsperaNocturna: res.resumen.horas_espera_nocturna,
      objetivo: res.resumen.objetivo,
      material: res.resumen.material,
      fuente: res.fuente,
      comparativa: res.resumen.comparativa_bagnold ?? null,
    },
    riskSegments: (riesgo?.segments ?? []).map((seg, i) => ({
      from: [seg.from.lon, seg.from.lat],
      to: [seg.to.lon, seg.to.lat],
      distance_m: seg.distance_m,
      risk: seg.risk,
      warnings: seg.warnings ?? [],
      blocking: blocking.has(i),
    })),
    riskLevel: riesgo?.risk_level ?? null,
    overallRisk: riesgo?.overall_risk ?? null,
    warnings: riesgo ? riskWarnings(res) : derivedWarnings(res),
    coveragePct:
      res.control_calidad?.pct_celdas_validas ?? res.control_calidad?.pct_validas ?? null,
  }
}

const SLOPE_COLORS = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  extreme: '#ef4444',
  unknown: '#9ca3af',
} as const

export function slopeColor(degrees: number): string {
  if (!Number.isFinite(degrees)) return SLOPE_COLORS.unknown
  if (degrees < 5) return SLOPE_COLORS.low
  if (degrees < 10) return SLOPE_COLORS.medium
  if (degrees < 15) return SLOPE_COLORS.high
  return SLOPE_COLORS.extreme
}

export function riskScoreLevel(risk: number | null): string {
  if (risk === null || !Number.isFinite(risk)) return 'unknown'
  if (risk < 1 / 3) return 'low'
  if (risk < 2 / 3) return 'medium'
  return 'high'
}

export function riskScoreColor(risk: number | null): string {
  return riskLevelColor(riskScoreLevel(risk))
}
