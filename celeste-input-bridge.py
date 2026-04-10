#!/usr/bin/env python3
"""
celeste-input-bridge.py

The reason this exists: OBS browser sources on Wayland can't capture keyboard
input because the underlying library (libuiohook) doesn't support Wayland.
This script works around that by reading directly from /dev/input via evdev,
then forwarding key events to the overlay over a local WebSocket.

Two things are running here:
  - HTTP server on port 16901: serves the overlay HTML so OBS can load it
    from localhost instead of a file:// URL (file:// blocks WebSocket on some setups)
  - WebSocket server on port 16900: pushes key_pressed / key_released events
    to any connected clients (i.e. the overlay running in OBS)
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


# serve the overlay HTML over HTTP so OBS can load it as a proper URL.
# runs in a daemon thread so it doesn't block the async event loop.
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HTML_DIR, **kw)
    def log_message(self, *_):
        pass  # don't spam the terminal with HTTP request logs

def start_http():
    with TCPServer(('127.0.0.1', PORT + 1), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_http, daemon=True).start()
print(f'HTML served at http://localhost:{PORT + 1}/celeste-overlay.html')


# evdev keycodes → Windows scan codes.
# the overlay HTML uses Windows scan codes because that's what most input
# overlay tooling expects — regular keys map 1:1, extended keys (arrows etc.)
# get the 0xE000 prefix that marks them as extended PS/2 scan codes.
# if your bindings are different, change the left side of each entry.
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

# connected WebSocket clients — in practice this is just OBS, but the
# set handles it gracefully if something else connects too
clients = set()


def find_keyboards():
    """
    Grab every /dev/input device that looks like a keyboard.
    The check for KEY_A filters out things like media remotes and mice
    that technically send EV_KEY events but aren't full keyboards.
    Requires the user to be in the 'input' group.
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
    """Send a message to all connected clients. Errors on individual sends
    are swallowed — a client disconnecting mid-send shouldn't crash everything."""
    if clients:
        await asyncio.gather(*[c.send(msg) for c in list(clients)], return_exceptions=True)


async def handle_client(ws):
    """Track connected WebSocket clients so broadcast() knows who to send to."""
    clients.add(ws)
    print(f'client connected ({len(clients)} total)')
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)
        print(f'client disconnected ({len(clients)} remaining)')


async def read_keyboard(dev):
    """
    Read raw events from one keyboard device and forward mapped keys.
    event.value: 1 = key down, 0 = key up, 2 = repeat (held).
    We ignore repeats — the overlay only needs to know pressed/released.
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

    # start the WebSocket server and all keyboard readers concurrently
    server = await websockets.serve(handle_client, '127.0.0.1', PORT)
    print(f'websocket listening on ws://localhost:{PORT}')

    await asyncio.gather(
        server.serve_forever(),
        *[read_keyboard(kb) for kb in keyboards],
    )

asyncio.run(main())
