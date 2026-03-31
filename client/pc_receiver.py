import asyncio
import json
import signal
from aiohttp import ClientSession, WSMsgType
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

RELAY_URL = "wss://phantom-arm-webservice.onrender.com/ws/inputroom?role=receiver"

mouse = MouseController()
keyboard = KeyboardController()

SPECIAL_KEYS = {
    "space": Key.space,
    "enter": Key.enter,
    "esc": Key.esc,
    "tab": Key.tab,
    "backspace": Key.backspace,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
}


def to_button(name: str):
    return {
        "left": Button.left,
        "right": Button.right,
        "middle": Button.middle,
    }[name]


def to_key(name: str):
    return SPECIAL_KEYS.get(name, name)


def execute_event(raw: str):
    ev = json.loads(raw)
    kind = ev["kind"]

    if kind == "mouse_move":
        dx = int(ev.get("dx", 0))
        dy = int(ev.get("dy", 0))

        dx = max(-200, min(200, dx))
        dy = max(-200, min(200, dy))

        x, y = mouse.position
        mouse.position = (x + dx, y + dy)

    elif kind == "mouse_button":
        button = to_button(ev["button"])
        state = ev["state"]
        if state == "down":
            mouse.press(button)
        elif state == "up":
            mouse.release(button)

    elif kind == "key":
        key = to_key(ev["key"])
        state = ev["state"]
        if state == "press":
            keyboard.press(key)
        elif state == "release":
            keyboard.release(key)

    else:
        print("unknown event:", ev)


async def main():
    stop = asyncio.Event()

    def _stop():
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    async with ClientSession() as session:
        async with session.ws_connect(RELAY_URL, heartbeat=20) as ws:
            print("connected to relay as receiver")

            async def receiver_loop():
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        print("received:", msg.data)
                        try:
                            execute_event(msg.data)
                            await ws.send_str(json.dumps({"ok": True, "received": True}))
                        except Exception as e:
                            print("execute error:", e)
                            await ws.send_str(json.dumps({"ok": False, "error": str(e)}))
                    elif msg.type == WSMsgType.ERROR:
                        print("websocket error:", ws.exception())
                        break

            recv_task = asyncio.create_task(receiver_loop())
            await stop.wait()
            recv_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())