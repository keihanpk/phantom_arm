import asyncio
import json
import signal
from aiohttp import ClientSession, WSMsgType

RELAY_URL = "wss://phantom-arm-webservice.onrender.com/ws/inputroom?role=sender"


async def send_events(ws):
    seq = 1

    events = [
        {"seq": seq , "kind": "mouse_move", "dx": 20, "dy": -20},
        {"seq": seq +2  , "kind": "mouse_move", "dx": -20, "dy": 20},
        {"seq": seq +3  , "kind": "mouse_move", "dx": -20, "dy": -20},
        {"seq": seq +4  , "kind": "mouse_move", "dx": 20, "dy": 20},
        {"seq": seq +5, "kind": "mouse_move", "dx": 20, "dy": -20},
        {"seq": seq +6  , "kind": "mouse_move", "dx": -20, "dy": 20},
        {"seq": seq +7  , "kind": "mouse_move", "dx": -20, "dy": -20},
        {"seq": seq +8  , "kind": "mouse_move", "dx": 20, "dy": 20},
        {"seq": seq +9  , "kind": "mouse_move", "dx": 15, "dy": -15},
        {"seq": seq +10 , "kind": "mouse_move", "dx": -15, "dy": 15},
        {"seq": seq +11 , "kind": "mouse_move", "dx": 10, "dy": 10},
        {"seq": seq +12 , "kind": "mouse_move", "dx": -10, "dy": -10},
        {"seq": seq +13 , "kind": "mouse_move", "dx": 25, "dy": 10},
        {"seq": seq +14 , "kind": "mouse_move", "dx": -25, "dy": -10},
        {"seq": seq +15 , "kind": "mouse_move", "dx": 5, "dy": -25},
        {"seq": seq +16 , "kind": "mouse_move", "dx": -3, "dy": 3},
        {"seq": seq +17 , "kind": "mouse_move", "dx": -3, "dy": 3},
        {"seq": seq +18 , "kind": "mouse_move", "dx": -3, "dy": 3},
        {"seq": seq +19 , "kind": "mouse_move", "dx": -3, "dy": 3},
        {"seq": seq +20 , "kind": "mouse_move", "dx": -3, "dy": 3},
        # {"seq": seq +1 , "kind": "mouse_button", "button": "left", "state": "down"},
        # {"seq": seq  + 2, "kind": "mouse_button", "button": "left", "state": "up"},
        # {"seq": seq  + 3, "kind": "key", "key": "space", "state": "press"},
        # {"seq": seq  + 4, "kind": "key", "key": "space", "state": "release"},
    ]

    await asyncio.sleep(1.0)

    for ev in events:
        payload = json.dumps(ev)
        await ws.send_str(payload)
        print("sent:", payload)
        await asyncio.sleep(0.3)

    # keep connection open for manual testing
    while True:
        await asyncio.sleep(30)


async def receive_messages(ws):
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            print("from receiver:", msg.data)
        elif msg.type == WSMsgType.ERROR:
            print("websocket error:", ws.exception())
            break


async def main():
    stop = asyncio.Event()

    def _stop():
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    async with ClientSession() as session:
        async with session.ws_connect(RELAY_URL, heartbeat=20) as ws:
            print("connected to relay as sender")

            recv_task = asyncio.create_task(receive_messages(ws))
            send_task = asyncio.create_task(send_events(ws))

            await stop.wait()

            recv_task.cancel()
            send_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())