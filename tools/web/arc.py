import math
from PIL import Image, ImageDraw, ImageFont
S = 8
COLOR = (253, 23, 23)
FONT = "C:/Windows/Fonts/NotoSansSC-VF.ttf"
def render(text, out, W, H, cx, cy, R, half_chord, upward, size):
    big = Image.new("L", (W * S, H * S), 0)
    f = ImageFont.truetype(FONT, size * S)
    try: f.set_variation_by_name(b"Black")
    except Exception: pass
    th = math.asin(half_chord / R)
    n = len(text)
    for i, ch in enumerate(text):
        a = -th + 2 * th * i / (n - 1)
        if upward:   # rainbow: centre below
            x, y, rot = cx + R * math.sin(a), cy - R * math.cos(a), -math.degrees(a)
        else:        # smile: centre above
            x, y, rot = cx + R * math.sin(a), cy + R * math.cos(a), math.degrees(a)
        g = Image.new("L", (size * S * 2, size * S * 2), 0)
        ImageDraw.Draw(g).text((size * S, size * S), ch, font=f, fill=255, anchor="mm")
        g = g.rotate(rot, resample=Image.BICUBIC)
        big.paste(255, (int(x * S - g.width / 2), int(y * S - g.height / 2)), g)
    a = big.resize((W, H), Image.LANCZOS)
    img = Image.new("RGBA", (W, H), COLOR + (0,)); img.putalpha(a)
    img.save(out)
    v = Image.new("RGBA", (W, H), (0, 0, 0, 255)); v.alpha_composite(img); v.resize((W * 4, H * 4), Image.NEAREST).save("view_" + out)
render("必须经过警长批准", "zh_text.png", 256, 44, 128, 13 + 300, 300, 106, True, 21)
render("才能访问互联网", "zh_text bottom.png", 256, 44, 131, 29 - 220, 220, 90, False, 21)
