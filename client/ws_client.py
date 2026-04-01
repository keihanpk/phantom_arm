import asyncio
import websockets

URI = "ws://127.0.0.1:8765"

async def send_loop(ws):
    while True:
        msg = await asyncio.to_thread(input, "send> ")
        await ws.send(msg)

async def recv_loop(ws):
    async for message in ws:
        print(f"\nrecv> {message}")

async def main():
    async with websockets.connect(
        URI,
        max_size=None,
        compression=None
    ) as ws:
        print("Connected to remote WebSocket server")

        await asyncio.gather(
            send_loop(ws),
            recv_loop(ws),
        )

if __name__ == "__main__":
    asyncio.run(main())