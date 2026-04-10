#!/usr/bin/env python3
"""
celeste-input-bridge.py

obs-plugin-input-overlay doesn't work on Wayland (libuiohook just doesn't support it),
so this reads from /dev/input directly and handles everything itself.

runs two things:
  - HTTP on 16901: serves the overlay HTML so OBS can load it from localhost
    instead of a file:// URL, which breaks WebSocket in some setups
  - WebSocket on 16900: sends key_pressed / key_released events to the overlay
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


# tiny HTTP server so OBS can load the overlay as a real URL.
# daemon thread so it doesn't block the async loop below.
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HTML_DIR, **kw)
    def log_message(self, *_):
        pass  # nobody needs to see GET requests in their terminal

def start_http():
    with TCPServer(('127.0.0.1', PORT + 1), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_http, daemon=True).start()
print(f'HTML served at http://localhost:{PORT + 1}/celeste-overlay.html')


# evdev keycodes → Windows scan codes.
# regular keys map 1:1, arrow keys and other extended keys get the 0xE000 prefix
# (that's just how PS/2 extended scan codes work).
# change the left side of each line if your bindings are different.
KEYMAP = {
    ecodes.KEY_ESC:        0x0001,  # pause
    ecodes.KEY_C:          0x002E,  # jump
    ecodes.KEY_UP:         0xE048,  # up
    ecodes.KEY_LEFT:       0xE04B,  # left
    ecodes.KEY_RIGHT:      0xE04D,  # right
    ecodes.KEY_DOWN:       0xE050,  # down
    ecodes.KEY_X:          0x002D,  # dash
    ecodes.KEY_LEFTSHIFT:  0x002A,  # grab
    ecodes.KEY_A:          0x001E,  # jump (alt)
    ecodes.KEY_D:          0x0020,  # demo
    ecodes.KEY_LEFTCTRL:   0x001D,  # talk / interact
}

# connected WebSocket clients — realistically just OBS, but a set works fine if anything else connects
clients = set()


def find_keyboards():
    """
    Find every /dev/input device that looks like a keyboard.
    Checking for KEY_A filters out mice and media remotes that send EV_KEY events
    but aren't actual keyboards. needs the user to be in the 'input' group.
    """
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
    """Send to all connected clients. Individual send errors are swallowed so
    a client disconnecting mid-send doesn't take everything else down."""
    if clients:
        await asyncio.gather(*[c.send(msg) for c in list(clients)], return_exceptions=True)


async def handle_client(ws):
    """Just tracks who's connected so broadcast() has someone to send to."""
    clients.add(ws)
    print(f'client connected ({len(clients)} total)')
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)
        print(f'client disconnected ({len(clients)} remaining)')


async def read_keyboard(dev):
    """
    Read events from one keyboard and forward the ones we care about.
    event.value is 1 for key down, 0 for key up, 2 for held repeat.
    Repeats get ignored — the overlay just needs pressed/released.
    """
    async for event in dev.async_read_loop():
        if event.type != ecodes.EV_KEY or event.value == 2:
            continue

        wincode = KEYMAP.get(event.code)
        if wincode is None:
            continue  # not a key we care about

        etype = 'key_pressed' if event.value == 1 else 'key_released'
        await broadcast(json.dumps({'event_type': etype, 'keycode': wincode}))


async def main():
    print('celeste input bridge starting...')
    keyboards = find_keyboards()
    if not keyboards:
        print('no keyboards found in /dev/input — are you in the "input" group?')
        sys.exit(1)

    # run the WebSocket server and all keyboard readers at the same time
    server = await websockets.serve(handle_client, '127.0.0.1', PORT)
    print(f'websocket listening on ws://localhost:{PORT}')

    await asyncio.gather(
        server.serve_forever(),
        *[read_keyboard(kb) for kb in keyboards],
    )

asyncio.run(main())
