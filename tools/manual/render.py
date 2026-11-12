"""Manual page re-typesetter.

Usage:
  python render.py grid  <page>        -> grids/<page>.png  (original + 50px grid with labels)
  python render.py lines <page>        -> prints detected text-line boxes (dark/colored ink rows)
  python render.py render <page>       -> zh/<page>.png from specs/<page>.json, plus cmp/<page>.png (side by side)

<page> is the png basename without extension, e.g. 01_1-1

Spec (specs/<page>.json):
{
  "erase": [[x0,y0,x1,y1], ...],          # extra regions to paint with background (optional)
  "blocks": [
    {"box":[x0,y0,x1,y1],                 # region: erased, then text drawn inside it
     "text":"中文，可以用 {#a040c0|SELECT} 着色片段，用 **粗体**，\n 表示强制换行",
     "size":30,                           # px, auto-shrinks if it doesn't fit
     "font":"serif"|"sans"|"mono",        # default serif
     "weight":"Regular"|"Bold"|"SemiBold"|"Medium",
     "color":"#000000", "align":"left"|"center"|"right",
     "valign":"top"|"middle", "line":1.35,  # line height multiplier
     "erase":true,                        # set false to draw over without erasing
     "bg":"#ffffff"                       # optional explicit background (default: auto-detected mode color of the box)
    }
  ]
}
"""
import sys, os, json, re
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = {
    "serif": "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
    "sans": "C:/Windows/Fonts/NotoSansSC-VF.ttf",
    "mono": "C:/Windows/Fonts/NotoSansSC-VF.ttf",
}
_cache = {}


def font(kind, weight, size):
    key = (kind, weight, size)
    if key not in _cache:
        f = ImageFont.truetype(FONTS.get(kind, FONTS["serif"]), size)
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
        _cache[key] = f
    return _cache[key]


def parse(text, base_color):
    """-> list of (token, color, bold). Tokens: single CJK chars, latin words, spaces, '\n'."""
    spans = []
    pat = re.compile(r"\{(#[0-9a-fA-F]{6})\|(.*?)\}|\*\*(.*?)\*\*", re.S)
    pos = 0
    for m in pat.finditer(text):
        if m.start() > pos:
            spans.append((text[pos:m.start()], base_color, False))
        if m.group(1):
            inner = m.group(2)
            bold = False
            if inner.startswith("**") and inner.endswith("**"):
                inner, bold = inner[2:-2], True
            spans.append((inner, m.group(1), bold))
        else:
            spans.append((m.group(3), base_color, True))
        pos = m.end()
    if pos < len(text):
        spans.append((text[pos:], base_color, False))
    toks = []
    for s, c, b in spans:
        for t in re.findall(r"\n|[A-Za-z0-9_.,'\"()=*<>%$#@!?:/\-+]+|\s|.", s):
            toks.append((t, c, b))
    return toks


NO_START = set("，。、；：！？）》」』”’…—,.;:!?)")


def layout(toks, kind, weight, size, width):
    lines, cur, w = [], [], 0
    for t, c, b in toks:
        if t == "\n":
            lines.append(cur); cur, w = [], 0; continue
        f = font(kind, "Bold" if b else weight, size)
        tw = f.getlength(t)
        if w + tw > width and cur and not (t in NO_START and w + tw <= width + size):
            if t.isspace():
                lines.append(cur); cur, w = [], 0; continue
            lines.append(cur); cur, w = [], 0
        cur.append((t, c, b, tw)); w += tw
    lines.append(cur)
    return lines


def bg_color(img, box):
    x0, y0, x1, y1 = box
    crop = img.crop((x0, y0, x1, y1)).convert("RGB")
    crop = crop.resize((max(1, (x1 - x0) // 4), max(1, (y1 - y0) // 4)))
    return Counter(crop.getdata()).most_common(1)[0][0]


def render(page):
    spec = json.load(open(os.path.join(HERE, "specs", page + ".json"), encoding="utf-8"))
    src = Image.open(os.path.join(HERE, page + ".png"))
    mode = src.mode
    img = src.convert("RGBA")
    d = ImageDraw.Draw(img)
    for box in spec.get("erase", []):
        bg = bg_color(img, box)
        d.rectangle(box, fill=bg)
    for blk in spec["blocks"]:
        x0, y0, x1, y1 = blk["box"]
        if blk.get("erase", True):
            bg = blk.get("bg") or bg_color(src.convert("RGBA"), blk["box"])
            d.rectangle([x0, y0, x1, y1], fill=bg)
        kind = blk.get("font", "serif"); weight = blk.get("weight", "Regular")
        size = int(blk.get("size", 30)); lh = blk.get("line", 1.35)
        color = blk.get("color", "#000000")
        toks = parse(blk["text"], color)
        while True:
            lines = layout(toks, kind, weight, size, x1 - x0)
            total = len(lines) * size * lh
            if total <= (y1 - y0) + size * 0.3 or size <= 12:
                break
            size -= 1
        if size != int(blk.get("size", 30)):
            print(f"  [shrink] block at {blk['box']} -> size {size}")
        y = y0
        if blk.get("valign") == "middle":
            y = y0 + ((y1 - y0) - total) / 2
        for ln in lines:
            lw = sum(t[3] for t in ln)
            if blk.get("align") == "center":
                x = x0 + ((x1 - x0) - lw) / 2
            elif blk.get("align") == "right":
                x = x1 - lw
            else:
                x = x0
            for t, c, b, tw in ln:
                f = font(kind, "Bold" if b else weight, size)
                d.text((x, y + (size * lh - size) / 2), t, font=f, fill=c)
                x += tw
            y += size * lh
    os.makedirs(os.path.join(HERE, "zh"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "cmp"), exist_ok=True)
    out = img if mode == "RGBA" else img.convert("RGB")
    out.save(os.path.join(HERE, "zh", page + ".png"))
    cmp = Image.new("RGB", (src.width * 2 + 10, src.height), "gray")
    cmp.paste(src.convert("RGB"), (0, 0)); cmp.paste(img.convert("RGB"), (src.width + 10, 0))
    cmp = cmp.resize((cmp.width // 2, cmp.height // 2))
    cmp.save(os.path.join(HERE, "cmp", page + ".png"))
    print("wrote zh/%s.png and cmp/%s.png" % (page, page))


def grid(page):
    img = Image.open(os.path.join(HERE, page + ".png")).convert("RGB")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    for x in range(0, img.width, 50):
        d.line([(x, 0), (x, img.height)], fill=(0, 200, 255) if x % 100 else (255, 0, 0), width=1)
        if x % 100 == 0: d.text((x + 2, 2), str(x), fill=(255, 0, 0), font=f)
    for y in range(0, img.height, 50):
        d.line([(0, y), (img.width, y)], fill=(0, 200, 255) if y % 100 else (255, 0, 0), width=1)
        if y % 100 == 0: d.text((2, y + 2), str(y), fill=(255, 0, 0), font=f)
    os.makedirs(os.path.join(HERE, "grids"), exist_ok=True)
    img.save(os.path.join(HERE, "grids", page + ".png"))
    print("wrote grids/%s.png" % page)


def lines(page):
    img = Image.open(os.path.join(HERE, page + ".png")).convert("RGB")
    W, H = img.size
    px = img.load()
    bg = bg_color(img.convert("RGBA"), (0, 0, W, H))[:3]
    def ink(p):
        return sum(abs(a - b) for a, b in zip(p, bg)) > 120
    rows = []
    for y in range(H):
        xs = [x for x in range(0, W, 2) if ink(px[x, y])]
        rows.append((min(xs), max(xs)) if xs else None)
    y = 0
    while y < H:
        if rows[y]:
            y0 = y; xa, xb = rows[y]
            while y < H and rows[y]:
                xa = min(xa, rows[y][0]); xb = max(xb, rows[y][1]); y += 1
            if y - y0 >= 4:
                print(f"y {y0:4d}-{y:4d}  x {xa:4d}-{xb:4d}  h={y - y0}")
        y += 1


if __name__ == "__main__":
    cmd, page = sys.argv[1], sys.argv[2]
    {"grid": grid, "lines": lines, "render": render}[cmd](page)
