import { http, HttpResponse } from 'msw'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { loadFixture } from '../test/handlers'
import { server } from '../test/server'
import {
  CoreError,
  getBaseLayers,
  getHealth,
  getRasterBand,
  postRoute,
  searchPlaces,
} from './coreClient'
import type { RouteRequest } from './types'

const ROUTE_REQUEST: RouteRequest = {
  lon: 137.4416,
  lat: -4.5895,
  material: 'hematita',
  sol: 1360,
  hora: 9,
  vmax: 1000,
}

describe('coreClient', () => {
  beforeAll(() => {
    URL.createObjectURL = vi.fn(() => 'blob:mock')
  })

  describe('happy path', () => {
    it('getHealth parses the live fixture', async () => {
      const health = await getHealth()
      expect(health.status).toBe('ok')
      expect(health.servicios.ms6).toBe('ok')
      expect(health.servicios.ms1).toBe('ok')
      expect(health.fallback_precalculado).toBe(true)
      expect(health.sols).toEqual([1360, 2140, 3290, 4710])
      expect(health.aoi).toEqual([137.345, -4.74, 137.455, -4.58])
      expect(health.bounds_rejilla).toHaveLength(4)
    })

    it('getBaseLayers parses the Core FeatureCollection snapshot', async () => {
      const layers = await getBaseLayers()
      expect(layers.type).toBe('FeatureCollection')
      expect(layers.features).toHaveLength(23)
      const capas = new Set(layers.features.map((f) => f.properties?.capa))
      expect(capas).toEqual(new Set(['puntos_quimica', 'traza_msl', 'origen']))
    })

    it('getRasterBand returns an object URL and parsed X-Bounds', async () => {
      let query = ''
      server.use(
        http.get('/api/capas/raster/:banda', ({ request }) => {
          query = new URL(request.url).search
          return new HttpResponse(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), {
            headers: { 'Content-Type': 'image/png', 'X-Bounds': '137.345,-4.74,137.455,-4.58' },
          })
        }),
      )
      const raster = await getRasterBand('pendiente_grados', 'viridis')
      expect(query).toContain('cmap=viridis')
      expect(URL.createObjectURL).toHaveBeenCalled()
      expect(raster.url).toBe('blob:mock')
      expect(raster.bounds).toEqual([137.345, -4.74, 137.455, -4.58])
    })

    it('postRoute sends the request body and parses the route fixture', async () => {
      let body: unknown
      server.use(
        http.post('/api/ruta', async ({ request }) => {
          body = await request.json()
          return HttpResponse.json(loadFixture('route.json'))
        }),
      )
      const route = await postRoute(ROUTE_REQUEST)
      expect(body).toEqual(ROUTE_REQUEST)
      expect(route.fuente).toBe('ms6')
      expect(route.resumen.objetivo).toBe('Oudam')
      expect(route.resumen.distancia_km).toBe(7.73)
      expect(route.tramos).toHaveLength(13)
      expect(route.riesgo?.risk_level).toBe('medium')
      const capas = route.geojson.features.map((f) => f.properties?.capa)
      expect(capas).toContain('ruta_optima')
      expect(capas).toContain('contrafactual')
      expect(capas).toContain('objetivo')
      expect(capas).toContain('origen')
    })

    it('searchPlaces returns proxied MS1 results', async () => {
      const res = await searchPlaces('Glen Etive', 5)
      expect(res.total).toBe(1)
      expect(res.results[0]?.place.name).toBe('Glen Etive')
      expect(res.results[0]?.place.center).toEqual({ lat: -4.7303, lon: 137.3835 })
    })

    it('calls the relative /api base only (no hardcoded host)', async () => {
      let url = ''
      server.use(
        http.get('*/api/health', ({ request }) => {
          url = request.url
          return HttpResponse.json(loadFixture('health.live.json'))
        }),
      )
      await getHealth()
      expect(new URL(url).pathname).toBe('/api/health')
    })
  })

  describe('edge cases', () => {
    it('postRoute abort propagates AbortError, not CoreError', async () => {
      const controller = new AbortController()
      const promise = postRoute(ROUTE_REQUEST, controller.signal)
      controller.abort()
      await expect(promise).rejects.toSatisfy(
        (e) => !(e instanceof CoreError) && (e as Error).name === 'AbortError',
      )
    })

    it('postRoute accepts riesgo: null when MS5 is unavailable', async () => {
      const fixture = loadFixture<Record<string, unknown>>('route.json')
      server.use(
        http.post('/api/ruta', () =>
          HttpResponse.json({ ...fixture, fuente: 'precalculada', riesgo: null }),
        ),
      )
      const route = await postRoute(ROUTE_REQUEST)
      expect(route.riesgo).toBeNull()
      expect(route.fuente).toBe('precalculada')
    })

    it('getRasterBand rejects a response without a valid X-Bounds header', async () => {
      server.use(
        http.get(
          '/api/capas/raster/:banda',
          () =>
            new HttpResponse(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), {
              headers: { 'Content-Type': 'image/png' },
            }),
        ),
      )
      await expect(getRasterBand('albedo', 'gray')).rejects.toSatisfy(
        (e) => !(e instanceof CoreError) && /X-Bounds/i.test((e as Error).message),
      )
    })
  })

  describe('failure', () => {
    it('non-2xx throws CoreError with status and string detail (400/404)', async () => {
      server.use(
        http.post('/api/ruta', () =>
          HttpResponse.json({ detail: 'origen fuera del AOI' }, { status: 400 }),
        ),
      )
      const err = await postRoute(ROUTE_REQUEST).catch((e: unknown) => e)
      expect(err).toBeInstanceOf(CoreError)
      expect((err as CoreError).status).toBe(400)
      expect((err as CoreError).detail).toBe('origen fuera del AOI')
      expect((err as CoreError).message).toBe('origen fuera del AOI')
    })

    it('503 without a route backend surfaces the Core detail string', async () => {
      server.use(
        http.post('/api/ruta', () =>
          HttpResponse.json(
            { detail: 'sin backend de ruta disponible para esta solicitud' },
            { status: 503 },
          ),
        ),
      )
      await expect(postRoute(ROUTE_REQUEST)).rejects.toMatchObject({
        status: 503,
        detail: 'sin backend de ruta disponible para esta solicitud',
      })
    })

    it('422 joins the FastAPI validation detail list', async () => {
      server.use(
        http.post('/api/ruta', () =>
          HttpResponse.json(
            {
              detail: [
                { loc: ['body', 'hora'], msg: 'Input should be less than 24', type: 'less_than' },
                { loc: ['body', 'vmax'], msg: 'Input should be greater than 0', type: 'greater_than' },
              ],
            },
            { status: 422 },
          ),
        ),
      )
      const err = await postRoute(ROUTE_REQUEST).catch((e: unknown) => e)
      expect(err).toBeInstanceOf(CoreError)
      expect((err as CoreError).status).toBe(422)
      expect((err as CoreError).detail).toBe(
        'Input should be less than 24; Input should be greater than 0',
      )
    })

    it('raster 502 surfaces as CoreError', async () => {
      server.use(
        http.get('/api/capas/raster/:banda', () =>
          HttpResponse.json({ detail: 'raster ilegible' }, { status: 502 }),
        ),
      )
      await expect(getRasterBand('pendiente_grados')).rejects.toMatchObject({
        status: 502,
        detail: 'raster ilegible',
      })
    })

    it('places search 503 surfaces as CoreError', async () => {
      server.use(
        http.get('/api/lugares/buscar', () =>
          HttpResponse.json({ detail: 'location-service no configurado' }, { status: 503 }),
        ),
      )
      await expect(searchPlaces('Bradbury')).rejects.toMatchObject({
        status: 503,
        detail: 'location-service no configurado',
      })
    })
  })
})
