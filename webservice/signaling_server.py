import os
import json
from aiohttp import web

# room_id -> {"sender": ws|None, "receiver": ws|None}
rooms: dict[str, dict[str, web.WebSocketResponse | None]] = {}


async def healthcheck(_: web.Request) -> web.Response:
    return web.json_response({"ok": True, "rooms": len(rooms)})


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    room_id = request.match_info["room_id"]
    role = request.query.get("role")

    if role not in {"sender", "receiver"}:
        return web.Response(status=400, text="role must be sender or receiver")

    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    room = rooms.setdefault(room_id, {"sender": None, "receiver": None})

    old_ws = room.get(role)
    if old_ws is not None and not old_ws.closed:
        await old_ws.close()

    room[role] = ws
    print(f"[join] room={room_id} role={role}")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                text = msg.data
                print(f"[message] room={room_id} from={role} size={len(text)}")

                if role == "sender":
                    peer = room.get("receiver")
                    if peer is not None and not peer.closed:
                        await peer.send_str(text)
                elif role == "receiver":
                    # optional acknowledgements/debug path back to sender
                    peer = room.get("sender")
                    if peer is not None and not peer.closed:
                        await peer.send_str(text)

            elif msg.type == web.WSMsgType.ERROR:
                print(f"[ws-error] room={room_id} role={role} error={ws.exception()}")

    except Exception as e:
        print(f"[handler-error] room={room_id} role={role} error={e}")

    finally:
        if rooms.get(room_id, {}).get(role) is ws:
            rooms[room_id][role] = None

        room = rooms.get(room_id)
        if room and room["sender"] is None and room["receiver"] is None:
            rooms.pop(room_id, None)
            print(f"[leave] room={room_id} removed=true")
        else:
            print(f"[leave] room={room_id} role={role}")

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", healthcheck)
    app.router.add_get("/health", healthcheck)
    app.router.add_get("/ws/{room_id}", websocket_handler)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)