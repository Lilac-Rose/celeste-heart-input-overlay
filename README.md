# celeste-heart-input-overlay

Keyboard input overlay for Celeste speedruns, built for Linux + Wayland + OBS.

The layout is a heart shape with keys labelled by what they do rather than which key they are. The bridge reads directly from `/dev/input` via evdev, so it works even though OBS's built-in browser source blocks native key hooks on Wayland.

```
    JUMP       JUMP
GRAB  II  ▲  DASH DEMO
    ◀   ▼   ▶
        TALK
```

## How it works

- `celeste-input-bridge.py` — reads your keyboard via evdev and serves key events over a WebSocket on `localhost:16900`. It also hosts the HTML file over HTTP on `localhost:16901` so OBS can load it without `file://` security restrictions.
- `celeste-heart-input-overlay.html` — the actual overlay. It connects to the WebSocket and lights up keys as you press them.
- `gen-celeste-heart-input-overlay.py` — optional, generates a sprite sheet PNG + JSON config if you want to use obs-plugin-input-overlay instead of the browser source. Probably don't bother, the HTML approach is simpler.

## Requirements

- Python 3
- [`python-evdev`](https://python-evdev.readthedocs.io/) and `python-websockets` — on Arch: `sudo pacman -S python-evdev python-websockets`
- OBS with the browser source plugin (`obs-studio-browser` on Arch)
- Your user in the `input` group: `sudo usermod -aG input $USER` (then log out and back in)
- [Renogare](https://www.dafont.com/renogare.font) font installed to `~/.local/share/fonts/` — the overlay falls back to monospace if it's not there

## Setup

**1. Clone and place the files**

```bash
git clone https://github.com/Lilac-Rose/celeste-heart-input-overlay
cd celeste-heart-input-overlay
```

**2. Install the systemd service**

```bash
cp celeste-input-bridge.service ~/.config/systemd/user/
systemctl --user enable --now celeste-input-bridge.service
```

Update the `ExecStart` path in the service file if you cloned somewhere other than `~/Games/celeste-heart-input-overlay`.

**3. Add to OBS**

- Add a **Browser** source
- Set URL to `http://localhost:16901/celeste-heart-input-overlay.html`
- Width: **2048**, Height: **1632**
- Scale the source down on your canvas to whatever size looks right — it renders at 2K so it stays sharp at any size
- If the source is black: go to OBS Settings → Advanced → disable **Browser Source Hardware Acceleration**

That's it. The bridge starts automatically on login and reconnects if OBS restarts.

## Key bindings

These match the default Celeste bindings I use. If yours are different, edit the `KEYMAP` dict in `celeste-input-bridge.py` and the matching one in `celeste-heart-input-overlay.html`.

| Key | Action |
|-----|--------|
| Arrow keys | Move |
| C, A | Jump |
| X | Dash |
| LShift | Grab |
| D | Demo (debug) |
| LCtrl | Talk / Interact |
| Esc | Pause |

## Customising the look

All the colours and sizing are CSS variables at the top of `celeste-heart-input-overlay.html`. The dark purple theme is:

```css
background inactive: #2a003a
background active:   #7b00cc
border inactive:     #5a1080
border active:       #cc66ff
text inactive:       #9040c0
text active:         #ffffff
```

## Why not obs-plugin-input-overlay?

`libuiohook`, which that plugin uses for key capture, explicitly does not support Wayland. The plugin installs fine and even opens a WebSocket server, it just never sends any events. This project routes around that by reading from `/dev/input` directly.
