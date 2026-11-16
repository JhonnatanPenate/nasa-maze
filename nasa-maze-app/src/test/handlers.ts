import { http, HttpResponse } from 'msw'
import type { RasterBand } from '../api/types'

const fixtureModules = import.meta.glob<unknown>('./fixtures/*.json', {
  eager: true,
  import: 'default',
})

export function loadFixture<T = Record<string, unknown>>(name: string): T {
  const fixture = fixtureModules[`./fixtures/${name}`]
  if (fixture === undefined) throw new Error(`Unknown fixture: ${name}`)
  return fixture as T
}

const BANDAS: RasterBand[] = [
  'pendiente_grados',
  'rugosidad_m',
  'fraccion_oscura',
  'inercia_termica_tiu',
  'albedo',
  'distancia_duna_m',
]

const placesSearch = {
  query: 'Glen Etive',
  normalized_query: 'glen etive',
  total: 1,
  results: [
    {
      score: 1,
      match_type: 'exact_name',
      place: {
        id: 'mars:msl:glen-etive',
        name: 'Glen Etive',
        body: 'mars',
        kind: 'poi',
        feature_type: 'mission_target',
        source: 'mission_msl',
        center: { lat: -4.7303, lon: 137.3835 },
        bbox: null,
        diameter_km: null,
        elevation_m: null,
        approval_status: null,
        aliases: [],
        tags: [],
        properties: {},
        in_regions: ['aoi:gale-90m'],
      },
    },
  ],
  catalog_version: 'msl-2026.1',
  coordinate_system: {
    body: 'mars',
    crs: 'IAU_2015:49900',
    lat_type: 'planetocentric',
    lon_convention: 'east_positive_0_360',
    radius_m: 3396190,
  },
}

export const handlers = [
  http.get('/api/health', () => HttpResponse.json(loadFixture('health.live.json'))),
  http.get('/api/capas/base', () => HttpResponse.json(loadFixture('baseLayers.json'))),
  http.get('/api/capas/raster/:banda', ({ params }) => {
    if (!BANDAS.includes(String(params.banda) as RasterBand)) {
      return HttpResponse.json({ detail: `banda desconocida: ${params.banda}` }, { status: 404 })
    }
    return new HttpResponse(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), {
      headers: {
        'Content-Type': 'image/png',
        'X-Bounds': '137.345000,-4.740000,137.455000,-4.580000',
      },
    })
  }),
  http.post('/api/ruta', () => HttpResponse.json(loadFixture('route.json'))),
  http.get('/api/lugares/buscar', () => HttpResponse.json(placesSearch)),
]
