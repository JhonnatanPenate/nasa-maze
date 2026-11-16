import httpx


class RoutingUnavailableError(Exception):
    """MS6 no responde o falló (timeout, conexión, 5xx)."""


class RoutingClient:
    def __init__(self, base_url: str, timeout_s: float, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport)

    def post_route(self, payload: dict) -> httpx.Response:
        """Devuelve la respuesta de MS6 tal cual para 2xx/4xx; lanza RoutingUnavailableError en el resto."""
        try:
            resp = self._client.post("/route", json=payload)
        except httpx.HTTPError as e:
            raise RoutingUnavailableError(str(e)) from e
        if resp.status_code >= 500:
            raise RoutingUnavailableError(f"MS6 respondió {resp.status_code}")
        return resp
