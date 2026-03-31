import asyncio
import json
import signal
from typing import Optional

from aiohttp import ClientSession, WSMsgType
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription

# SIGNALING_URL = "ws://YOUR_VPS_OR_PUBLIC_HOST:8765/ws/inputroom"
SIGNALING_URL = "wss://phantom-arm-webservice.onrender.com/ws/inputroom"
GPU_TCP_HOST = "0.0.0.0"
GPU_TCP_PORT = 9001

pc: Optional[RTCPeerConnection] = None
channel = None
ws = None
gpu_clients = set()


async def send_signaling(message: dict):
    await ws.send_str(json.dumps(message))


async def consume_signaling():
    global pc
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            data = json.loads(msg.data)

            if data["type"] == "answer":
                await pc.setRemoteDescription(
                    RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                )
                print("Remote answer applied")

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


async def handle_gpu_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    gpu_clients.add(writer)
    print(f"GPU client connected: {addr}")

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            if channel and channel.readyState == "open":
                # Expect one JSON event per line from the GPU job.
                channel.send(line.decode("utf-8").rstrip("\n"))
            else:
                print("Data channel not open yet, dropping event")
    except Exception as e:
        print("GPU client error:", e)
    finally:
        gpu_clients.discard(writer)
        writer.close()
        await writer.wait_closed()
        print(f"GPU client disconnected: {addr}")


async def start_gpu_server():
    server = await asyncio.start_server(handle_gpu_client, GPU_TCP_HOST, GPU_TCP_PORT)
    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"GPU ingest listening on {sockets}")
    return server


async def main():
    global pc, channel, ws

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

    channel = pc.createDataChannel(
        "events",
        ordered=True,
    )

    @channel.on("open")
    def on_open():
        print("Data channel open")

    @channel.on("close")
    def on_close():
        print("Data channel closed")

    session = ClientSession()
    ws = await session.ws_connect(SIGNALING_URL, heartbeat=20)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await send_signaling(
        {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
    )

    gpu_server = await start_gpu_server()

    stop = asyncio.Event()

    def _stop():
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    signaling_task = asyncio.create_task(consume_signaling())

    await stop.wait()

    signaling_task.cancel()
    gpu_server.close()
    await gpu_server.wait_closed()
    await pc.close()
    await ws.close()
    await session.close()


if __name__ == "__main__":
    asyncio.run(main())