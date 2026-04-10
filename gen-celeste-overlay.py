#!/usr/bin/env python3
"""Generate Celeste input overlay sprite sheet + JSON config for obs-plugin-input-overlay.

Renders at 2x scale for crisp display. Set the OBS source display size to 152x90.
"""

from PIL import Image, ImageDraw, ImageFont
import json, os

# ── Key definitions ────────────────────────────────────────────────────────────
# (element-id, display-label, Windows scancode used by obs-plugin-input-overlay)
KEYS = [
    ('esc',   'II',   0x0001),  # Escape  → pause
    ('jump1', 'JUMP', 0x002E),  # C       → jump
    ('left',  '◀',   0xE04B),  # Left arrow
    ('down',  '▼',   0xE050),  # Down arrow
    ('up',    '▲',   0xE048),  # Up arrow
    ('right', '▶',   0xE04D),  # Right arrow
    ('dash',  'DASH', 0x002D),  # X       → dash
    ('grab',  'GRAB', 0x002A),  # LShift  → grab
    ('jump2', 'JUMP', 0x001E),  # A       → jump (alt)
    ('demo',  'DEMO', 0x0020),  # D       → demo
]

# ── Key dimensions ────────────────────────────────────────────────────────────
SCALE    = 1   # 1x — plugin handles display scaling in OBS
KW       = 64  # key width in sprite sheet (and display px)
KH       = 64  # key height
RADIUS   = 8
ROW_GAP  = 4   # gap between inactive and active rows in sprite sheet

# ── Dark-purple color scheme ───────────────────────────────────────────────────
BG_OFF     = (42,  0,   58,  255)   # #2a003a
BG_ON      = (123, 0,  204,  255)   # #7b00cc
BORDER_OFF = (90,  16, 128,  255)   # #5a1080
BORDER_ON  = (204, 102,255,  255)   # #cc66ff
TEXT_OFF   = (144, 64, 192,  255)   # #9040c0
TEXT_ON    = (255, 255,255,  255)   # #ffffff

# ── Overlay layout ─────────────────────────────────────────────────────────────
# KW=64, gap=4 → stride=68
#   Row 0 — bumps:   II at x=68,  JUMP at x=204         (y=0)
#   Row 1 — wide:    ◀▼▲▶DASH at x=0,68,136,204,272     (y=68)
#   Row 2 — narrow:  GRAB JUMP DEMO at x=68,136,204      (y=136)
STRIDE    = KW + 4
OVERLAY_W = 5 * STRIDE        # 340
OVERLAY_H = 3 * STRIDE        # 204

KEY_POS = {
    'esc':   (STRIDE * 1,  0),
    'jump1': (STRIDE * 3,  0),
    'left':  (STRIDE * 0,  STRIDE),
    'down':  (STRIDE * 1,  STRIDE),
    'up':    (STRIDE * 2,  STRIDE),
    'right': (STRIDE * 3,  STRIDE),
    'dash':  (STRIDE * 4,  STRIDE),
    'grab':  (STRIDE * 1,  STRIDE * 2),
    'jump2': (STRIDE * 2,  STRIDE * 2),
    'demo':  (STRIDE * 3,  STRIDE * 2),
}

# ── Sprite sheet layout ────────────────────────────────────────────────────────
# One column per key, two rows: top=inactive, bottom=active
N          = len(KEYS)
COL_STRIDE = KW + 4
SHEET_W    = N * COL_STRIDE
SHEET_H    = KH * 2 + ROW_GAP

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_PATH = os.path.expanduser('~/.local/share/fonts/Renogare-Regular.otf')
try:
    font    = ImageFont.truetype(FONT_PATH, 18)
    font_sm = ImageFont.truetype(FONT_PATH, 14)
    print('Using Renogare font ♡')
except Exception as e:
    print(f'Renogare not found ({e}), using default')
    font = font_sm = ImageFont.load_default()

ARROW_CHARS = set('◀▶▲▼')

ARROW_FONT_PATHS = [
    '/usr/share/fonts/TTF/JetBrainsMonoNerdFontMono-BoldItalic.ttf',
    '/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Light.ttf',
    '/usr/share/fonts/TTF/JetBrainsMonoNLNerdFontMono-BoldItalic.ttf',
]
arrow_font = None
for p in ARROW_FONT_PATHS:
    if os.path.exists(p):
        try:
            arrow_font = ImageFont.truetype(p, 22)
            print(f'Arrow font: {os.path.basename(p)}')
            break
        except Exception:
            pass
if arrow_font is None:
    arrow_font = font


def pick_font(label):
    if any(c in ARROW_CHARS for c in label):
        return arrow_font
    return font_sm if len(label) >= 3 else font


def draw_key(draw, x, y, label, bg, border, text_color):
    draw.rounded_rectangle(
        [x, y, x + KW - 1, y + KH - 1],
        radius=RADIUS,
        fill=bg,
        outline=border,
        width=SCALE,
    )
    f = pick_font(label)
    bbox = draw.textbbox((0, 0), label, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (KW - tw) // 2 - bbox[0]
    ty = y + (KH - th) // 2 - bbox[1]
    draw.text((tx, ty), label, font=f, fill=text_color)


# ── Generate sprite sheet ──────────────────────────────────────────────────────
sheet = Image.new('RGBA', (SHEET_W, SHEET_H), (0, 0, 0, 0))
draw  = ImageDraw.Draw(sheet)

sprite_coords = {}   # kid → (off_x, off_y, on_x, on_y)  — 2x pixel coords in sprite sheet

for col, (kid, label, code) in enumerate(KEYS):
    x      = col * COL_STRIDE
    y_off  = 0
    y_on   = KH + ROW_GAP

    draw_key(draw, x, y_off, label, BG_OFF, BORDER_OFF, TEXT_OFF)
    draw_key(draw, x, y_on,  label, BG_ON,  BORDER_ON,  TEXT_ON)

    sprite_coords[kid] = (x, y_off, x, y_on)

out_dir    = os.path.expanduser('~/Games/speedrun/')
png_path   = out_dir + 'celeste-keys.png'
json_path  = out_dir + 'celeste-keys.json'

sheet.save(png_path)
print(f'Saved sprite sheet: {SHEET_W}x{SHEET_H}px → {png_path}')

# ── Generate JSON config (4-value mapping matching preset format exactly) ─────
elements = []
for kid, label, code in KEYS:
    sx_off, sy_off, sx_on, sy_on = sprite_coords[kid]
    px, py = KEY_POS[kid]
    elements.append({
        'type':    1,
        'pos':     [px, py],
        'id':      kid,
        'z_level': 0,
        # 4-value: active sprite — plugin dims when not pressed, full on press
        'mapping': [sx_on, sy_on, KW, KH],
        'code':    code,
    })

config = {
    'default_width':  KW,
    'default_height': KH,
    'space_h':        4,
    'space_v':        4,
    'flags':          0,
    'overlay_width':  OVERLAY_W,
    'overlay_height': OVERLAY_H,
    'elements':       elements,
}

with open(json_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f'Saved JSON config → {json_path}')
print(f'OBS overlay canvas: {OVERLAY_W}x{OVERLAY_H}')
print()
print('Key layout:')
for kid, label, code in KEYS:
    px, py = KEY_POS[kid]
    print(f'  [{kid:6s}] "{label:3s}"  screen=({px:3d},{py:2d})  scancode=0x{code:04X}')
