import asyncio
import websockets

HOST = "127.0.0.1"
PORT = 8765

clients = set()

async def handler(websocket):
    clients.add(websocket)
    print("Client connected")

    try:
        async for message in websocket:
            print("Received:", message)

            # echo back
            await websocket.send(f"echo: {message}")

            # optional broadcast to all connected clients
            for client in clients:
                if client != websocket:
                    await client.send(f"broadcast: {message}")

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        clients.remove(websocket)

async def main():
    async with websockets.serve(
        handler,
        HOST,
        PORT,
        max_size=None,        # allow large messages
        compression=None      # disable compression for lower overhead
    ):
        print(f"WebSocket server running on ws://{HOST}:{PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())