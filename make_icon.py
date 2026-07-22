"""Generate assets/Logo.ico for the Valorant Decloak app.

Concept: an eye that reveals cloaked enemies, with a crosshair pupil,
on the iconic Valorant red disc.
"""
import os
from PIL import Image, ImageDraw

S = 1024
SS = 4               # supersample for crisp anti-aliasing
W = S * SS

RED      = (255, 70, 85, 255)     # Valorant red (#FF4655)
DARK_RED = (190, 41, 53, 255)
CREAM    = (236, 232, 224, 255)   # Valorant off-white
INK      = (24, 26, 33, 255)      # near-black

img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
cx, cy = W / 2, W / 2

# --- Outer red disc + thin ink ring ---
pad = int(W * 0.03)
d.ellipse([pad, pad, W - pad, W - pad], fill=RED)
inner = pad + int(W * 0.05)
d.ellipse([inner, inner, W - inner, W - inner], outline=INK, width=int(W * 0.012))

# --- Eye almond as a vesica (intersection of two circles) ---
def vesica_mask(half_w, half_h):
    """Smooth almond/eye outline mask via two overlapping circles."""
    m = Image.new("L", (W, W), 0)
    md = ImageDraw.Draw(m)
    R = (half_w**2 + half_h**2) / (2 * half_h)   # radius so circles meet at corners
    top_c = cy + (R - half_h)
    bot_c = cy - (R - half_h)
    a = Image.new("L", (W, W), 0)
    ImageDraw.Draw(a).ellipse([cx - R, top_c - R, cx + R, top_c + R], fill=255)
    b = Image.new("L", (W, W), 0)
    ImageDraw.Draw(b).ellipse([cx - R, bot_c - R, cx + R, bot_c + R], fill=255)
    return Image.composite(a, Image.new("L", (W, W), 0), b)

half_w, half_h = W * 0.355, W * 0.20
m_full = vesica_mask(half_w, half_h)

# cream eye-white
white = Image.new("RGBA", (W, W), CREAM)
img.paste(white, (0, 0), m_full)

# ink outline of the eye (full mask minus a slightly smaller mask)
m_in = vesica_mask(half_w - W * 0.018, half_h - W * 0.018)
outline = Image.composite(
    Image.new("RGBA", (W, W), INK),
    Image.new("RGBA", (W, W), (0, 0, 0, 0)),
    Image.composite(m_full, Image.new("L", (W, W), 0),
                    Image.eval(m_in, lambda p: 255 - p)),
)
img.alpha_composite(outline)

# --- Iris (red) + pupil (ink) clipped to the eye so it never spills past lids ---
iris = Image.new("RGBA", (W, W), (0, 0, 0, 0))
idd = ImageDraw.Draw(iris)
ir = W * 0.150
idd.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=RED, outline=INK, width=int(W * 0.014))
pr = W * 0.066
idd.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=INK)
hr = W * 0.024            # catch-light
idd.ellipse([cx - ir * 0.4 - hr, cy - ir * 0.4 - hr,
             cx - ir * 0.4 + hr, cy - ir * 0.4 + hr], fill=CREAM)
img.paste(iris, (0, 0), Image.composite(iris, Image.new("RGBA", (W, W), (0, 0, 0, 0)),
                                        m_full).split()[3])

# --- Crosshair through the pupil (FPS cue) ---
gap = W * 0.092
arm = W * 0.205
th = int(W * 0.026)
for x0, y0, x1, y1 in [
    (cx - arm, cy, cx - gap, cy),
    (cx + gap, cy, cx + arm, cy),
    (cx, cy - arm, cx, cy - gap),
    (cx, cy + gap, cx, cy + arm),
]:
    d.line([x0, y0, x1, y1], fill=CREAM, width=th)

# --- Downscale + export multi-resolution .ico ---
base = img.resize((S, S), Image.LANCZOS)
out = os.path.join("assets", "Logo.ico")
base.save(out, format="ICO",
          sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
base.save(os.path.join("assets", "Logo.png"))
print("wrote", out)
