#!/usr/bin/env python3
"""
THE DAILY OVERFIELD - reusable masthead template.

plate_template.jpg is fixed art: ornament, ribbons, wordmark, medallion, rules
and "TWO CENT EDITION". This script stamps on the one thing that changes:

    * date           (folio, flush left)

The weather panel was removed 2026-09-16. Its space on the left of the plate is
left blank by design.

    python3 masthead_template.py --date 2026-09-16
"""
import argparse, datetime
from PIL import Image, ImageDraw, ImageFont

PLATE = "plate_template.jpg"
B700  = "fonts/PlayfairDisplay-latin-700-normal.ttf"
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

def ordinal(n):
    suf = "TH" if (n % 100) in (11, 12, 13) else {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{suf}"

def folio_date(dt):
    return f"{dt.strftime('%A').upper()},  {dt.strftime('%B').upper()} {ordinal(dt.day)}, {dt.year}"

# ---------------------------------------------------------------------------
def build(dt, out="masthead_out.png"):
    base = Image.open(PLATE).convert("RGB")
    W, H = base.size
    L = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)

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
    p.add_argument("--out", default="masthead_out.png")
    a = p.parse_args()
    dt = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    print(build(dt, a.out))
