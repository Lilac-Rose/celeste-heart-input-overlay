# celeste-heart-input-overlay

Input overlay for Celeste on Linux + Wayland + OBS. obs-plugin-input-overlay doesn't work on Wayland so I ended up writing this instead.

Heart-shaped layout, keys labelled by action, dark purple theme.

```
    JUMP       JUMP
GRAB  II  ▲  DASH DEMO
    ◀   ▼   ▶
        TALK
```

## How it works

- `celeste-input-bridge.py` — reads keyboard input via evdev and sends key events to the overlay over a local WebSocket. Also serves the HTML on localhost so OBS can load it without file:// causing issues.
- `celeste-overlay.html` — the overlay itself. Lights up keys when you press them.

## Requirements

- Python 3
- [`python-evdev`](https://python-evdev.readthedocs.io/) and `python-websockets` — on Arch: `sudo pacman -S python-evdev python-websockets`
- OBS with browser source (`obs-studio-browser` on Arch)
- Your user in the `input` group: `sudo usermod -aG input $USER` then log out and back in
- [Renogare](https://www.dafont.com/renogare.font) font in `~/.local/share/fonts/` — falls back to monospace if missing

## Setup

**1. Clone it**

```bash
git clone https://github.com/Lilac-Rose/celeste-heart-input-overlay
cd celeste-heart-input-overlay
```

**2. Install the service**

```bash
cp celeste-input-bridge.service ~/.config/systemd/user/
systemctl --user enable --now celeste-input-bridge.service
```

If you cloned somewhere other than `~/Games/celeste-heart-input-overlay`, update the path in the service file first.

**3. Add to OBS**

- Add a **Browser** source
- URL: `http://localhost:16901/celeste-overlay.html`
- Width: **2048**, Height: **1632**
- Scale it down on your canvas to whatever size you want
- If it shows as a black box: OBS Settings → Advanced → turn off **Browser Source Hardware Acceleration**

The bridge starts on login and reconnects automatically if OBS restarts.

## Key bindings

My bindings — edit the `KEYMAP` in both files if yours are different.

| Key | Action |
|-----|--------|
| Arrow keys | Move |
| C, A | Jump |
| X | Dash |
| LShift | Grab |
| D | Demo |
| LCtrl | Talk |
| Esc | Pause |

## Changing the look

Colours and sizing are at the top of `celeste-overlay.html`.

```css
background inactive: #2a003a
background active:   #7b00cc
border inactive:     #5a1080
border active:       #cc66ff
text inactive:       #9040c0
text active:         #ffffff
```

## Why not obs-plugin-input-overlay?

It uses `libuiohook` for key capture which doesn't support Wayland, so it just doesn't work. The plugin runs fine and opens a WebSocket but never sends anything.
