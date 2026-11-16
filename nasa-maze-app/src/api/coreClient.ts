import type {
  BaseLayersResponse,
  HealthResponse,
  PlaceSearchResponse,
  RasterBand,
  RasterBandResult,
  RasterCmap,
  RouteRequest,
  RouteResponse,
} from './types'

const BASE = '/api'

export class CoreError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'CoreError'
    this.status = status
    this.detail = detail
  }
}

async function errorDetail(res: Response): Promise<string> {
  const fallback = res.statusText || `HTTP ${res.status}`
  try {
    const body: unknown = await res.json()
    const detail = (body as { detail?: unknown } | null)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item: unknown) =>
          typeof item === 'object' && item !== null && 'msg' in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join('; ')
    }
    return detail === undefined ? fallback : JSON.stringify(detail)
  } catch {
    return fallback
  }
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) throw new CoreError(res.status, await errorDetail(res))
  return res
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await apiFetch(path, { signal })
  return (await res.json()) as T
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson<HealthResponse>('/health', signal)
}

export function getBaseLayers(signal?: AbortSignal): Promise<BaseLayersResponse> {
  return getJson<BaseLayersResponse>('/capas/base', signal)
}

export async function getRasterBand(
  banda: RasterBand,
  cmap: RasterCmap = 'viridis',
  signal?: AbortSignal,
): Promise<RasterBandResult> {
  const res = await apiFetch(
    `/capas/raster/${encodeURIComponent(banda)}?cmap=${encodeURIComponent(cmap)}`,
    { signal },
  )
  const parts = res.headers.get('X-Bounds')?.split(',').map(Number)
  if (!parts || parts.length !== 4 || parts.some(Number.isNaN)) {
    throw new Error('Core raster response is missing a valid X-Bounds header')
  }
  const blob = await res.blob()
  return { url: URL.createObjectURL(blob), bounds: parts as [number, number, number, number] }
}

export function postRoute(req: RouteRequest, signal?: AbortSignal): Promise<RouteResponse> {
  return apiFetch('/ruta', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  }).then((res) => res.json() as Promise<RouteResponse>)
}

export function searchPlaces(
  q: string,
  limit = 10,
  signal?: AbortSignal,
): Promise<PlaceSearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) })
  return getJson<PlaceSearchResponse>(`/lugares/buscar?${params.toString()}`, signal)
}
