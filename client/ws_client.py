import asyncio
from websockets.asyncio.client import connect

URI = "ws://127.0.0.1:8765"

async def recv_loop(ws):
    async for msg in ws:
        print(f"\n[client recv] {msg}")

async def send_loop(ws):
    while True:
        msg = await asyncio.to_thread(input, "client send> ")
        await ws.send(msg)

async def main():
    async with connect(
        URI,
        compression=None,
        max_size=None,
    ) as ws:
        print("connected")
        await asyncio.gather(
            recv_loop(ws),
            send_loop(ws),
        )

if __name__ == "__main__":
    asyncio.run(main())