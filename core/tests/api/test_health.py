import httpx

MS6 = "http://ms6.test"


def test_health_con_ms6_ok(make_client):
    h = lambda request: httpx.Response(200, json={"status": "ok"})
    body = make_client(h, ms6_url=MS6).get("/api/health").json()
    assert body["status"] == "ok" and body["servicios"] == {"ms6": "ok", "ms4": "no_configurado", "ms1": "no_configurado"}
    assert body["aoi"] == [137.345, -4.74, 137.455, -4.58] and len(body["bounds_rejilla"]) == 4


def test_health_ms6_caido_con_fallback_sigue_ok(make_client):
    def h(request):
        raise httpx.ConnectError("down")

    r = make_client(h, ms6_url=MS6).get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["servicios"]["ms6"] == "down" and body["fallback_precalculado"] is True and body["status"] == "ok"


def test_health_todo_caido_es_degraded_pero_200(make_client, tmp_path):
    r = make_client(data_dir=str(tmp_path)).get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded" and body["bounds_rejilla"] is None
