import { describe, expect, it } from 'vitest'
import type { RouteResponse, Tramo } from '../api/types'
import { loadFixture } from '../test/handlers'
import {
  buildRouteView,
  riskScoreColor,
  riskScoreLevel,
  RouteViewError,
  slopeColor,
} from './routeView'

const route = () => structuredClone(loadFixture<RouteResponse>('route.json'))

describe('buildRouteView', () => {
  it('splits optimal segments, alternative, target and origin', () => {
    const view = buildRouteView(route())
    expect(view.segments).toHaveLength(2)
    expect(view.segments[0].tipo_suelo).toBe('regolito_compacto')
    expect(view.segments[0].coordinates[0]).toEqual([137.44141550676412, -4.589869303841997])
    expect(view.alternative?.nombre).toBe('ruta_modelo_global')
    expect(view.alternative?.coordinates.length).toBeGreaterThan(2)
    expect(view.target).toMatchObject({ nombre: 'Oudam', material: 'hematita' })
    expect(view.origin).toMatchObject({ nombre: 'Bradbury Landing', lon: 137.4416 })
  })

  it('maps resumen into KPIs and computes bounds over all features', () => {
    const view = buildRouteView(route())
    expect(view.kpis.distanciaKm).toBe(7.73)
    expect(view.kpis.horaLlegada).toBe('S+1 08:15')
    expect(view.kpis.dosisRadAcumUgy).toBe(247.8)
    expect(view.kpis.horasEsperaNocturna).toBe(13.84)
    expect(view.kpis.fuente).toBe('ms6')
    expect(view.bounds).toEqual([137.3577, -4.679452215638589, 137.4416, -4.5895])
  })

  it('exposes riesgo segments, level and blocking flags when present', () => {
    const view = buildRouteView(route())
    expect(view.riskLevel).toBe('medium')
    expect(view.overallRisk).toBe(0.347)
    expect(view.riskSegments).toHaveLength(2)
    expect(view.riskSegments[0].blocking).toBe(false)
    expect(view.riskSegments[1].blocking).toBe(true)
    expect(view.warnings).toContain('STEEP_SLOPE_29DEG')
    expect(view.warnings).toContain('Slope 29.1 deg >= profile block limit 25.0 deg')
  })

  it('handles a response without contrafactual route', () => {
    const res = route()
    res.geojson.features = res.geojson.features.filter((f) => f.properties.capa !== 'contrafactual')
    const view = buildRouteView(res)
    expect(view.alternative).toBeNull()
    expect(view.segments).toHaveLength(2)
  })

  it('derives warnings client-side when riesgo is null', () => {
    const res = route()
    res.riesgo = null
    const view = buildRouteView(res)
    expect(view.riskSegments).toEqual([])
    expect(view.riskLevel).toBeNull()
    expect(view.warnings.some((w) => /night/i.test(w))).toBe(true)
    expect(view.warnings).toHaveLength(1)
  })

  it('warns on steep slope and dune cells when riesgo is null', () => {
    const res = route()
    res.riesgo = null
    res.resumen.horas_espera_nocturna = 0
    res.resumen.comparativa_bagnold.celdas_duna_ruta_optima = 4
    res.tramos[0].inclinacion_max_grados = 16.2
    const view = buildRouteView(res)
    expect(view.warnings.some((w) => /slope/i.test(w))).toBe(true)
    expect(view.warnings.some((w) => /dune/i.test(w))).toBe(true)
    expect(view.warnings).toHaveLength(2)
  })

  it('tolerates control_calidad null and null tramos cells', () => {
    const res = route()
    res.control_calidad = null
    res.tramos = [null, res.tramos[0]] as unknown as Tramo[]
    const view = buildRouteView(res)
    expect(view.coveragePct).toBeNull()
    expect(view.segments).toHaveLength(2)
  })

  it('throws RouteViewError on malformed geojson', () => {
    expect(() =>
      buildRouteView({ ...route(), geojson: { type: 'FeatureCollection' } } as unknown as RouteResponse),
    ).toThrow(RouteViewError)
    const badFeature = route()
    badFeature.geojson.features[0] = {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: 'nope' },
      properties: { capa: 'ruta_optima' },
    } as unknown as RouteResponse['geojson']['features'][number]
    expect(() => buildRouteView(badFeature)).toThrow(RouteViewError)
  })

  it('throws RouteViewError when the route has no optimal segments', () => {
    const res = route()
    res.geojson.features = res.geojson.features.filter((f) => f.properties.capa !== 'ruta_optima')
    expect(() => buildRouteView(res)).toThrow(RouteViewError)
  })
})

describe('slopeColor', () => {
  it('uses green < 5, yellow 5-10, orange 10-15, red >= 15', () => {
    expect(slopeColor(4.9)).toBe(slopeColor(0))
    expect(slopeColor(5)).not.toBe(slopeColor(4.9))
    expect(slopeColor(10)).not.toBe(slopeColor(9.9))
    expect(slopeColor(15)).not.toBe(slopeColor(14.9))
    expect(slopeColor(20)).toBe(slopeColor(15))
  })

  it('returns a neutral color for non-finite slopes', () => {
    expect(slopeColor(Number.NaN)).toBe('#9ca3af')
  })
})

describe('riskScoreLevel / riskScoreColor', () => {
  it('maps scores to risk levels and null to unknown', () => {
    expect(riskScoreLevel(null)).toBe('unknown')
    expect(riskScoreLevel(0.1)).toBe('low')
    expect(riskScoreLevel(0.5)).toBe('medium')
    expect(riskScoreLevel(0.9)).toBe('high')
  })

  it('returns a color per level', () => {
    expect(riskScoreColor(null)).not.toBe(riskScoreColor(0.9))
    expect(riskScoreColor(0.9)).toBe(riskScoreColor(0.8))
  })
})
