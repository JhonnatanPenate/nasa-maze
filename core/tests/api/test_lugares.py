import httpx

MS1 = "http://ms1.test"
RESULTADO = {"query": "oudam", "total": 1, "results": [{"score": 1.0, "place": {"name": "Oudam"}}]}


def test_buscar_passthrough(make_client):
    seen = {}

    def handler(request: httpx.Request):
        seen["path"], seen["params"] = request.url.path, dict(request.url.params)
        return httpx.Response(200, json=RESULTADO)

    r = make_client(handler, ms1_url=MS1).get("/api/lugares/buscar", params={"q": "oudam", "limit": 3})
    assert r.status_code == 200 and r.json() == RESULTADO
    assert seen == {"path": "/v1/places/search", "params": {"q": "oudam", "limit": "3"}}


def test_buscar_sin_resultados_es_200(make_client):
    h = lambda request: httpx.Response(200, json={"query": "zzz", "total": 0, "results": []})
    r = make_client(h, ms1_url=MS1).get("/api/lugares/buscar", params={"q": "zzz"})
    assert r.status_code == 200 and r.json()["results"] == []


def test_error_4xx_de_ms1_se_reenvia(make_client):
    h = lambda request: httpx.Response(422, json={"title": "Unprocessable", "status": 422})
    r = make_client(h, ms1_url=MS1).get("/api/lugares/buscar", params={"q": "x"})
    assert r.status_code == 422 and r.json()["status"] == 422


def test_sin_ms1_configurado_es_503(client):
    assert client.get("/api/lugares/buscar", params={"q": "oudam"}).status_code == 503


def test_ms1_caido_es_503(make_client):
    def h(request):
        raise httpx.ConnectError("down")

    assert make_client(h, ms1_url=MS1).get("/api/lugares/buscar", params={"q": "oudam"}).status_code == 503


def test_ms1_5xx_es_503(make_client):
    h = lambda request: httpx.Response(500)
    assert make_client(h, ms1_url=MS1).get("/api/lugares/buscar", params={"q": "oudam"}).status_code == 503


def test_parametros_invalidos_es_422_sin_llamar_a_ms1(make_client):
    def h(request):
        raise AssertionError("no debe llamar a MS1")

    c = make_client(h, ms1_url=MS1)
    assert c.get("/api/lugares/buscar").status_code == 422
    assert c.get("/api/lugares/buscar", params={"q": ""}).status_code == 422
    assert c.get("/api/lugares/buscar", params={"q": "x", "limit": 99}).status_code == 422
