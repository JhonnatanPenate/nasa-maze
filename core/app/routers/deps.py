import httpx


def get_transport() -> httpx.BaseTransport | None:
    """Los tests lo sobreescriben con un MockTransport."""
    return None
