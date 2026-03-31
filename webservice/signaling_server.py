import asyncio
import json
from aiohttp import web

rooms = {}  # room_id -> set(ws)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    room_id = request.match_info["room_id"]
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    peers = rooms.setdefault(room_id, set())
    peers.add(ws)

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                for peer in list(peers):
                    if peer is not ws and not peer.closed:
                        await peer.send_str(msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                print(f"websocket error: {ws.exception()}")
    finally:
        peers.discard(ws)
        if not peers:
            rooms.pop(room_id, None)

    return ws


app = web.Application()
app.router.add_get("/ws/{room_id}", websocket_handler)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8765)