import asyncio
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from ecohash import api_routes, client, connections
from tests.test_client import _mock_response
from tests.test_conversions import _png_b64


def test_settings_routes_and_generation_are_explicit():
    async def run():
        routes = web.RouteTableDef()
        api_routes.register_routes(routes)
        app = web.Application()
        app.add_routes(routes)
        async with TestClient(TestServer(app)) as browser:
            payload = {"name": "Studio", "base_url": "https://private.example/v1", "api_key": "private-secret"}
            response = await browser.put("/ecohash/connections/studio", json=payload)
            assert response.status == 403
            assert not connections.CONNECTIONS_PATH.exists()
            headers = {"X-EcoHash-Settings": "1"}
            response = await browser.put("/ecohash/connections/studio", json=payload, headers={**headers, "Origin": "https://untrusted.example"})
            assert response.status == 403
            response = await browser.put("/ecohash/connections/studio", json=payload, headers=headers)
            assert response.status == 200
            assert "private-secret" not in await response.text()
            response = await browser.get("/ecohash/connections")
            assert "private-secret" not in await response.text()
            assert response.headers["Cache-Control"] == "no-store"

            with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"id": "private-model"}]})) as request:
                response = await browser.post("/ecohash/connections/studio/test", json={}, headers=headers)
                assert response.status == 200
                assert (await response.json())["status"] == "ok"
                assert request.call_args.args == ("GET", "https://private.example/v1/models")
                response = await browser.post("/ecohash/connections/studio/generate-test", json={"model": "private-model"}, headers=headers)
                assert response.status == 400
                assert request.call_count == 1

            with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"b64_json": _png_b64()}]})) as request:
                response = await browser.post("/ecohash/connections/studio/generate-test", json={"model": "private-model", "confirm_generation": True}, headers=headers)
                assert response.status == 200
                assert (await response.json())["image"]
                assert request.call_args.args == ("POST", "https://private.example/v1/images/generations")
            response = await browser.delete("/ecohash/connections/studio", headers=headers)
            assert response.status == 200
    asyncio.run(run())


def test_api_invalid_inputs_do_not_disclose_keys():
    async def run():
        routes = web.RouteTableDef()
        api_routes.register_routes(routes)
        app = web.Application()
        app.add_routes(routes)
        async with TestClient(TestServer(app)) as browser:
            headers = {"X-EcoHash-Settings": "1"}
            response = await browser.put("/ecohash/connections/studio", json={"api_key": {"value": "private-secret"}}, headers=headers)
            assert response.status == 400
            assert "private-secret" not in await response.text()
            response = await browser.put("/ecohash/connections/studio", data="not json", headers=headers)
            assert response.status == 400
            response = await browser.get("/ecohash/models/missing")
            assert response.status == 400
            assert "not configured" in (await response.json())["error"]
    asyncio.run(run())
