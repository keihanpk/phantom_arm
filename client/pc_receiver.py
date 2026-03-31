import asyncio
import json
import signal
from typing import Optional

from aiohttp import ClientSession, WSMsgType
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

#SIGNALING_URL = "ws://YOUR_VPS_OR_PUBLIC_HOST:8765/ws/inputroom"
SIGNALING_URL = "wss://phantom-arm-webservice.onrender.com/ws/inputroom"

pc: Optional[RTCPeerConnection] = None
ws = None

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

        # Safety clamp
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
        print("Unknown event:", ev)


async def send_signaling(message: dict):
    await ws.send_str(json.dumps(message))


async def consume_signaling():
    global pc

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            data = json.loads(msg.data)

            if data["type"] == "offer":
                await pc.setRemoteDescription(
                    RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                )
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await send_signaling(
                    {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
                )

            elif data["type"] == "candidate":
                candidate = data["candidate"]
                if candidate is not None:
                    await pc.addIceCandidate(candidate)

            elif data["type"] == "bye":
                print("Received bye")
                break

        elif msg.type == WSMsgType.ERROR:
            print("WebSocket error:", ws.exception())
            break


async def main():
    global pc, ws

    config = RTCConfiguration(
        iceServers=[
            RTCIceServer(urls=["stun:stun.l.google.com:19302"])
        ]
    )
    pc = RTCPeerConnection(configuration=config)

    @pc.on("icecandidate")
    async def on_icecandidate(candidate):
        if candidate is not None:
            await send_signaling({"type": "candidate", "candidate": candidate})
        else:
            await send_signaling({"type": "candidate", "candidate": None})

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state:", pc.connectionState)

    @pc.on("datachannel")
    def on_datachannel(channel):
        print("Got data channel:", channel.label)

        @channel.on("message")
        def on_message(message):
            if isinstance(message, str):
                execute_event(message)
            else:
                print("Unexpected binary message")

    session = ClientSession()
    ws = await session.ws_connect(SIGNALING_URL, heartbeat=20)

    stop = asyncio.Event()

    def _stop():
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    signaling_task = asyncio.create_task(consume_signaling())

    await stop.wait()

    signaling_task.cancel()
    await pc.close()
    await ws.close()
    await session.close()


if __name__ == "__main__":
    asyncio.run(main())