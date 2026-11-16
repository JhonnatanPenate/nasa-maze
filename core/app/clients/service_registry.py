import httpx


def ping(url: str, timeout_s: float, transport: httpx.BaseTransport | None = None) -> str:
    if not url:
        return "no_configurado"
    try:
        with httpx.Client(base_url=url.rstrip("/"), timeout=timeout_s, transport=transport) as c:
            return "ok" if c.get("/health").status_code == 200 else "down"
    except httpx.HTTPError:
        return "down"
