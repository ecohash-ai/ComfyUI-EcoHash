"""ComfyUI routes for the connection manager. All responses are secret-free."""

import asyncio
from urllib.parse import urlsplit

from aiohttp import web

from . import client, connections, discovery


def _guard(request):
    if request.headers.get("X-EcoHash-Settings") != "1":
        raise web.HTTPForbidden(reason="Use the EcoHash connection manager.")
    origin = request.headers.get("Origin")
    try:
        valid_origin = not origin or urlsplit(origin).netloc == request.host
    except ValueError:
        valid_origin = False
    if not valid_origin:
        raise web.HTTPForbidden(reason="Cross-origin settings requests are not allowed.")


async def _result(operation, *args, **kwargs):
    try:
        result = await asyncio.to_thread(operation, *args, **kwargs)
        return web.json_response(result, headers={"Cache-Control": "no-store"})
    except client.EcoHashError as exc:
        return web.json_response({"error": str(exc)}, status=400, headers={"Cache-Control": "no-store"})


async def _body(request):
    try:
        data = await request.json()
    except (ValueError, UnicodeError):
        raise web.HTTPBadRequest(reason="Expected a JSON object.") from None
    if not isinstance(data, dict):
        raise web.HTTPBadRequest(reason="Expected a JSON object.")
    return data


def register_routes(routes):
    @routes.get("/ecohash/connections")
    async def list_connections(request):
        return await _result(connections.list_connections)

    @routes.put("/ecohash/connections/{connection}")
    async def save_connection(request):
        _guard(request)
        return await _result(connections.save_connection, request.match_info["connection"], await _body(request))

    @routes.delete("/ecohash/connections/{connection}")
    async def delete_connection(request):
        _guard(request)

        def remove():
            connections.delete_connection(request.match_info["connection"])
            return {"ok": True}

        return await _result(remove)

    @routes.post("/ecohash/connections/{connection}/test")
    async def test_connection(request):
        _guard(request)
        return await _result(discovery.test_connection, request.match_info["connection"])

    @routes.get("/ecohash/models/{connection}")
    async def models(request):
        return await _result(discovery.models, request.match_info["connection"], refresh=request.query.get("refresh") == "1")

    @routes.post("/ecohash/connections/{connection}/generate-test")
    async def generate_test(request):
        _guard(request)
        data = await _body(request)
        model = data.get("model")
        if not isinstance(model, str) or not model.strip():
            raise web.HTTPBadRequest(reason="Enter a deployed model ID.")
        if data.get("confirm_generation") is not True:
            raise web.HTTPBadRequest(reason="Confirm the billable generation test explicitly.")

        def generate():
            try:
                from ..ecohash_nodes.image_nodes import _generate
            except ImportError:
                from ecohash_nodes.image_nodes import _generate
            from . import conversions
            import base64

            connection_id = request.match_info["connection"]
            endpoint = None if connection_id == "public" else connections.resolve(connection_id)
            (image,) = _generate(model.strip(), "a small red apple on a plain white background, product photo", "512x512", 0, 42, endpoint)
            return {"image": base64.b64encode(conversions.image_tensor_to_png_bytes(image)).decode(), "width": image.shape[2], "height": image.shape[1]}

        return await _result(generate)

    @routes.post("/ecohash/connections/{connection}/chat-test")
    async def chat_test(request):
        _guard(request)
        data = await _body(request)
        model = data.get("model")
        if not isinstance(model, str) or not model.strip():
            raise web.HTTPBadRequest(reason="Enter a deployed language model ID.")
        if data.get("confirm_inference") is not True:
            raise web.HTTPBadRequest(reason="Confirm the billable text inference test explicitly.")

        def complete():
            try:
                from ..ecohash_nodes.llm_nodes import _run
            except ImportError:
                from ecohash_nodes.llm_nodes import _run
            connection_id = request.match_info["connection"]
            endpoint = None if connection_id == "public" else connections.resolve(connection_id)
            (text,) = _run(model.strip(), "chat", "Say hello in one short sentence.", "", 0.7, 1024, endpoint)
            return {"text": text}

        return await _result(complete)
