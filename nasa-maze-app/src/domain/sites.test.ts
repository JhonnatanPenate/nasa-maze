import { describe, expect, it } from 'vitest'
import type { BaseLayersResponse } from '../api/types'
import { loadFixture } from '../test/handlers'
import {
  bradburyOrigin,
  candidateSites,
  chemSites,
  mslTraverse,
  originOptions,
} from './sites'

const layers = () => loadFixture<BaseLayersResponse>('baseLayers.json')

describe('chemSites', () => {
  it('parses all 21 CheMin sites with coordinates', () => {
    const sites = chemSites(layers())
    expect(sites).toHaveLength(21)
    for (const s of sites) {
      expect(s.nombre).toBeTruthy()
      expect(Number.isFinite(s.lon)).toBe(true)
      expect(Number.isFinite(s.lat)).toBe(true)
    }
  })

  it('keeps null pct columns without crashing', () => {
    const rocknest = chemSites(layers()).find((s) => s.nombre === 'Rocknest')
    expect(rocknest?.pct.hematita).toBeNull()
  })
})

describe('candidateSites', () => {
  it('returns outcrops with a positive pct for the mineral (Oudam for hematite)', () => {
    const candidates = candidateSites(chemSites(layers()), 'hematita')
    expect(candidates.map((s) => s.nombre)).toContain('Oudam')
    for (const s of candidates) expect(s.pct.hematita).toBeGreaterThan(0)
  })

  it('returns only sites whose pct is > 0', () => {
    const all = chemSites(layers())
    for (const s of candidateSites(all, 'sulfatos')) {
      expect(s.pct.sulfatos).toBeGreaterThan(0)
    }
  })

  it('returns an empty list when every pct column is null', () => {
    const empty: BaseLayersResponse = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [137.4, -4.6] },
          properties: { capa: 'puntos_quimica', nombre: 'Null Site' },
        },
      ],
    }
    expect(candidateSites(chemSites(empty), 'hematita')).toEqual([])
  })
})

describe('bradburyOrigin / mslTraverse', () => {
  it('locates the Bradbury landing origin', () => {
    expect(bradburyOrigin(layers())).toMatchObject({
      nombre: 'Bradbury Landing',
      lon: 137.4416,
      lat: -4.5895,
    })
  })

  it('extracts the MSL traverse as coordinate lines', () => {
    const traverse = mslTraverse(layers())
    expect(traverse.length).toBeGreaterThan(0)
    expect(traverse[0][0]).toHaveLength(2)
  })
})

describe('originOptions', () => {
  it('lists Bradbury first, then the CheMin sites', () => {
    const options = originOptions(layers())
    expect(options[0].nombre).toBe('Bradbury Landing')
    expect(options.map((o) => o.nombre)).toContain('Oudam')
  })

  it('dedupes sites sharing the same coordinates', () => {
    const options = originOptions(layers())
    const coincident = options.filter(
      (o) => o.nombre === 'John Klein' || o.nombre === 'Cumberland',
    )
    expect(coincident).toHaveLength(1)
    const keys = options.map((o) => `${o.lon.toFixed(4)},${o.lat.toFixed(4)}`)
    expect(new Set(keys).size).toBe(keys.length)
  })
})
