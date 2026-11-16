import httpx


class LocationUnavailableError(Exception):
    """MS1 no responde o falló (timeout, conexión, 5xx)."""


def search_places(
    base_url: str, params: dict, timeout_s: float, transport: httpx.BaseTransport | None = None
) -> httpx.Response:
    """Devuelve la respuesta de MS1 tal cual para 2xx/4xx; lanza LocationUnavailableError en el resto."""
    try:
        with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport) as c:
            resp = c.get("/v1/places/search", params=params)
    except httpx.HTTPError as e:
        raise LocationUnavailableError(str(e)) from e
    if resp.status_code >= 500:
        raise LocationUnavailableError(f"MS1 respondió {resp.status_code}")
    return resp
