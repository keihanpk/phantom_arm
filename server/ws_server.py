import asyncio
from websockets.asyncio.server import serve

clients = set()

async def recv_loop(ws):
    async for msg in ws:
        print(f"[server recv] {msg}")

        # broadcast received message to all connected clients
        for client in list(clients):
            if client.closed:
                clients.discard(client)
                continue
            await client.send(f"[broadcast] {msg}")

async def send_loop(ws):
    while True:
        msg = await asyncio.to_thread(input, "server send> ")
        await ws.send(f"[server] {msg}")

async def handler(ws):
    print("client connected")
    clients.add(ws)
    try:
        await asyncio.gather(
            recv_loop(ws),
            send_loop(ws),
        )
    except Exception as e:
        print("server error:", e)
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