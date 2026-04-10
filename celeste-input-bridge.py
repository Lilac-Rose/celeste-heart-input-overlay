#!/usr/bin/env python3
"""
Celeste input overlay bridge.
- Serves the HTML overlay at http://localhost:16900/
- Serves key events as WebSocket at ws://localhost:16900/
In OBS: Browser source → URL → http://localhost:16900/
"""

import asyncio
import json
import sys
import os
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import threading
import evdev
from evdev import InputDevice, ecodes
import websockets

PORT     = 16900
HTML_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Tiny HTTP server for the overlay HTML ──────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HTML_DIR, **kw)
    def log_message(self, *_):
        pass  # suppress request logs

def start_http():
    with TCPServer(('127.0.0.1', PORT + 1), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_http, daemon=True).start()
print(f'HTML served at http://localhost:{PORT + 1}/celeste-overlay.html')

PORT = 16900

# evdev keycode → Windows scan code (matches HTML overlay KEYMAP)
KEYMAP = {
    ecodes.KEY_ESC:        0x0001,
    ecodes.KEY_C:          0x002E,
    ecodes.KEY_UP:         0xE048,
    ecodes.KEY_LEFT:       0xE04B,
    ecodes.KEY_RIGHT:      0xE04D,
    ecodes.KEY_DOWN:       0xE050,
    ecodes.KEY_X:          0x002D,
    ecodes.KEY_LEFTSHIFT:  0x002A,
    ecodes.KEY_A:          0x001E,
    ecodes.KEY_D:          0x0020,
    ecodes.KEY_LEFTCTRL:   0x001D,
}

clients = set()


def find_keyboards():
    keyboards = []
    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            if ecodes.EV_KEY in caps and ecodes.KEY_A in caps[ecodes.EV_KEY]:
                keyboards.append(dev)
                print(f'  keyboard: {dev.name} ({dev.path})')
        except Exception:
            pass
    return keyboards


async def broadcast(msg):
    if clients:
        await asyncio.gather(*[c.send(msg) for c in list(clients)], return_exceptions=True)


async def handle_client(ws):
    clients.add(ws)
    print(f'OBS connected ({len(clients)} client(s))')
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)
        print(f'OBS disconnected ({len(clients)} client(s))')


async def read_keyboard(dev):
    async for event in dev.async_read_loop():
        if event.type != ecodes.EV_KEY or event.value == 2:
            continue
        wincode = KEYMAP.get(event.code)
        if wincode is None:
            continue
        etype = 'key_pressed' if event.value == 1 else 'key_released'
        await broadcast(json.dumps({'event_type': etype, 'keycode': wincode}))


async def main():
    print('Celeste input bridge starting...')
    keyboards = find_keyboards()
    if not keyboards:
        print('ERROR: No keyboard found. Are you in the "input" group?')
        sys.exit(1)

    server = await websockets.serve(handle_client, '127.0.0.1', PORT)
    print(f'Listening on ws://localhost:{PORT}')

    await asyncio.gather(
        server.serve_forever(),
        *[read_keyboard(kb) for kb in keyboards],
    )

asyncio.run(main())
