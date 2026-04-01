import asyncio
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

clients = set()

async def recv_loop(ws):
    try:
        async for msg in ws:
            print(f"\n[server recv] {msg}")

            dead = []
            for client in clients:
                if client is ws:
                    continue
                try:
                    await client.send(f"[broadcast] {msg}")
                except ConnectionClosed:
                    dead.append(client)

            for client in dead:
                clients.discard(client)

    except ConnectionClosed:
        pass

async def send_loop(ws):
    try:
        while True:
            msg = await asyncio.to_thread(input, "server send> ")
            await ws.send(f"[server] {msg}")
    except ConnectionClosed:
        pass

async def handler(ws):
    print("client connected")
    clients.add(ws)
    try:
        await asyncio.gather(
            recv_loop(ws),
            send_loop(ws),
        )
    finally:
        clients.discard(ws)
        print("client disconnected")

async def main():
    async with serve(
        handler,
        "127.0.0.1",
        8765,
        compression=None,
        max_size=None,
    ):
        print("listening on ws://127.0.0.1:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())