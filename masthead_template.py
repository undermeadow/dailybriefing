#!/usr/bin/env python3
"""
THE DAILY OVERFIELD - reusable masthead template.

plate_template.jpg is fixed art: ornament, ribbons, wordmark, medallion, rules
and "TWO CENT EDITION". This script stamps on the two things that change:

    * weather panel  (left block, almanac-column layout)
    * date           (folio, flush left)

    python3 masthead_template.py --cond "Mostly Sunny" --hi 85 --lo 62 --rain 5
"""
import argparse, datetime, math
from PIL import Image, ImageDraw, ImageFont

PLATE = "plate_template.jpg"
B700  = "fonts/PlayfairDisplay-latin-700-normal.ttf"
B400  = "fonts/PlayfairDisplay-latin-400-normal.ttf"
I400  = "fonts/PlayfairDisplay-latin-400-italic.ttf"
INK   = (52, 47, 28)   # sampled off the plate: warm olive-black, not neutral
SS    = 3              # supersample factor

# --- geometry measured off the original artwork (2970 x 1466) ---------------
FOLIO_BASE  = 1343      # baseline of the folio row
FOLIO_CAP   = 41        # cap height of the folio type
FOLIO_TRACK = 1.2
FOLIO_LEFT  = 219       # left edge of the folio row. Held the issue number until
                        # 2026-09-15; the date now sets flush left from here.
                        # "TWO CENT EDITION" is baked into the plate at x2192-2757,
                        # so the date has 219-2192 to run in before it would collide.
WX_CX       = 380       # centre line of the weather panel
WX_HALF     = 210       # half-width of its rules

_k = {}
def capk(p):
    if p not in _k:
        f = ImageFont.truetype(p, 200)
        im = Image.new("L", (500, 500), 0)
        ImageDraw.Draw(im).text((60, 60), "H", font=f, fill=255)
        b = im.getbbox(); _k[p] = (b[3] - b[1]) / 200.0
    return _k[p]

def F(p, cap):  return ImageFont.truetype(p, max(4, int(round(cap / capk(p)))))
def tw(d, t, f, tr): return sum(d.textlength(c, font=f) for c in t) + tr * (len(t) - 1)

def T(d, t, f, x, base, tr=0, anchor="c"):
    w = tw(d, t, f, tr)
    if   anchor == "c": x -= w / 2
    elif anchor == "r": x -= w
    asc, _ = f.getmetrics()
    for c in t:
        d.text((x, base - asc), c, font=f, fill=INK)
        x += d.textlength(c, font=f) + tr

def fit(d, t, path, cap, maxw, tr):
    """shrink until the line fits the panel width"""
    while cap > 8:
        f = F(path, cap)
        if tw(d, t, f, tr) <= maxw: return f
        cap *= 0.94
    return F(path, cap)

def rule(d, y, h, half=WX_HALF):
    d.rectangle([(WX_CX - half) * SS, y * SS, (WX_CX + half) * SS, (y + h) * SS], fill=INK)

def vrule(d, x, w, y0, y1):
    d.rectangle([x * SS, y0 * SS, (x + w) * SS, y1 * SS], fill=INK)

def ordinal(n):
    suf = "TH" if (n % 100) in (11, 12, 13) else {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{suf}"

def folio_date(dt):
    return f"{dt.strftime('%A').upper()},  {dt.strftime('%B').upper()} {ordinal(dt.day)}, {dt.year}"

# ---------------------------------------------------------------------------
def build(dt, cond, hi, lo, rain, out="masthead_out.png"):
    base = Image.open(PLATE).convert("RGB")
    W, H = base.size
    L = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    cx = WX_CX * SS

    # ---- weather panel: almanac column ----
    # The panel grows SIDEWAYS, never downwards: the condition always sets on one
    # line and the block widens to hold it, so the height is constant and can
    # never reach the folio rules.
    HALF_MIN, HALF_MAX, PAD = 210, 330, 38
    CAP_COND = 46 * SS

    cond_t = cond.title()
    need = tw(d, cond_t, F(I400, CAP_COND), SS)
    HALF = int(min(HALF_MAX, max(HALF_MIN, need / SS / 2 + PAD + 16)))
    maxw = ((HALF - 16) * 2 - PAD) * SS

    cap = CAP_COND      # shrink only if even the widest block cannot hold it
    while cap > 8 and tw(d, cond_t, F(I400, cap), SS) > maxw:
        cap *= 0.96
    f_cond = F(I400, cap)

    y = 838
    y_top = y

    y += 78
    T(d, "WEATHER FORECAST", fit(d, "WEATHER FORECAST", B700, 34 * SS, maxw, 6 * SS),
      cx, y * SS, tr=6 * SS)

    y += 68
    T(d, cond_t, f_cond, cx, y * SS, tr=SS)

    y += 74
    T(d, f"HIGH {round(hi)}\u00b0", F(B700, 38 * SS), cx, y * SS, tr=2 * SS)
    y += 52
    T(d, f"LOW {round(lo)}\u00b0", F(B700, 38 * SS), cx, y * SS, tr=2 * SS)
    y += 52
    T(d, f"RAIN {round(rain)} PER CENT",
      fit(d, f"RAIN {round(rain)} PER CENT", B400, 28 * SS, maxw, 2 * SS),
      cx, y * SS, tr=2 * SS)

    y += 28
    y_bot = y + 16
    for side in (-1, 1):
        outer = WX_CX + side * HALF - (6 if side == 1 else 0)
        inner = WX_CX + side * (HALF - 16) - (2.4 if side == 1 else 0)
        vrule(d, outer, 6,   y_top, y_bot)
        vrule(d, inner, 2.4, y_top, y_bot)

    # ---- folio ----
    f_folio = F(B700, FOLIO_CAP * SS)
    T(d, folio_date(dt), f_folio, FOLIO_LEFT * SS, FOLIO_BASE * SS,
      tr=FOLIO_TRACK * SS, anchor="l")

    sm = L.resize((W, H), Image.LANCZOS)
    base.paste(sm.convert("RGB"), (0, 0), sm.split()[3])
    base.save(out)
    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    p.add_argument("--cond", required=True)
    p.add_argument("--hi", type=float, required=True)
    p.add_argument("--lo", type=float, required=True)
    p.add_argument("--rain", type=float, default=0)
    p.add_argument("--out", default="masthead_out.png")
    a = p.parse_args()
    dt = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    print(build(dt, a.cond, a.hi, a.lo, a.rain, a.out))
