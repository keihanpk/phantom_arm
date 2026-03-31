import json
import socket
import time

LOGIN_NODE_HOST = "YOUR_LOGIN_NODE_HOSTNAME"
LOGIN_NODE_PORT = 9001

events = [
    {"seq": 1, "kind": "mouse_move", "dx": 0, "dy": -20},
    {"seq": 2, "kind": "mouse_button", "button": "left", "state": "down"},
    {"seq": 3, "kind": "mouse_button", "button": "left", "state": "up"},
    {"seq": 4, "kind": "key", "key": "space", "state": "press"},
    {"seq": 5, "kind": "key", "key": "space", "state": "release"},
]

with socket.create_connection((LOGIN_NODE_HOST, LOGIN_NODE_PORT)) as s:
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    for ev in events:
        payload = json.dumps(ev).encode("utf-8") + b"\n"
        s.sendall(payload)
        time.sleep(0.03)