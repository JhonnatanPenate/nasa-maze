import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/health', () =>
    HttpResponse.json({
      status: 'ok',
      servicios: { ms6: 'ok', ms5: 'ok', ms4: 'ok', ms1: 'ok' },
    }),
  ),
]
