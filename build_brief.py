#!/usr/bin/env python3
"""
THE DAILY OVERFIELD - briefing PDF builder.

Renders the masthead, then sets the briefing body underneath it as an ordinary
readable document (single column, headings, lists, tables) and prints to PDF.

    python3 build_brief.py --body brief.md --out "Overfield-Daily-YYYY-MM-DD.pdf"

No weather arguments: the weather panel was removed 2026-09-16.
"""
import argparse, base64, datetime, subprocess, os
import masthead_template as mt

# WeasyPrint rather than wkhtmltopdf: this container's wkhtmltopdf is built
# against unpatched Qt, so --footer-html and --print-media-type are silently
# ignored, which means no page numbers and no control over page breaks.

F = "fonts"
PAPER = (238, 221, 196)     # sampled off the plate's own paper, away from the vignette

def b64(p): return base64.b64encode(open(p, "rb").read()).decode()

def paper_tile(path="paper_tile.png", n=512):
    """low-contrast grain over the plate's paper tone, so the page doesn't read as
    flat digital cream next to the textured masthead"""
    import numpy as np
    from PIL import Image, ImageFilter
    if os.path.exists(path): return path
    rng = np.random.default_rng(4)
    g = rng.normal(0, 1.0, (n, n))
    g = np.array(Image.fromarray(((g - g.min()) / (g.max() - g.min()) * 255).astype("uint8"))
                 .filter(ImageFilter.GaussianBlur(0.6))).astype(float)
    g = (g - g.mean()) / (g.std() or 1) * 2.1          # ~+/-2 levels, barely there
    arr = np.clip(np.dstack([g, g, g]) + np.array(PAPER, float), 0, 255)
    Image.fromarray(arr.astype("uint8")).save(path)
    return path

def match_paper(im, px=10):
    """Flatten the plate's own vignette so its paper equals the page paper, then
    feather the last few pixels. Correction is weighted by how paper-like each
    pixel is, so the ink keeps its density instead of being lifted with it."""
    import numpy as np, cv2
    from PIL import Image
    a = np.asarray(im).astype(np.float32)
    lum = a.mean(axis=2)
    w = np.clip((lum - 120.0) / 80.0, 0, 1)                 # 1 on paper, 0 on ink

    # local paper tone: blur the image with the ink masked out of the average
    num = cv2.GaussianBlur(a * w[:, :, None], (0, 0), 90)
    den = cv2.GaussianBlur(w, (0, 0), 90)[:, :, None] + 1e-6
    field = num / den                                       # smooth paper-only tone

    a = a + (np.array(PAPER, np.float32) - field) * w[:, :, None]

    h, wd, _ = a.shape
    m = np.ones((h, wd), np.float32)
    ramp = np.linspace(0, 1, px)
    m[:px, :] *= ramp[:, None]; m[-px:, :] *= ramp[::-1, None]
    m[:, :px] *= ramp[None, :]; m[:, -px:] *= ramp[None, ::-1]
    a = a * m[:, :, None] + np.array(PAPER, np.float32) * (1 - m[:, :, None])
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))

CSS = """
@font-face{font-family:'Body';src:url(data:font/ttf;base64,%(bk)s) format('truetype');font-weight:400;font-style:normal}
@font-face{font-family:'Body';src:url(data:font/ttf;base64,%(bi)s) format('truetype');font-weight:400;font-style:italic}
@font-face{font-family:'Body';src:url(data:font/ttf;base64,%(bb)s) format('truetype');font-weight:700;font-style:normal}
@font-face{font-family:'Body';src:url(data:font/ttf;base64,%(bbi)s) format('truetype');font-weight:700;font-style:italic}
@font-face{font-family:'Head';src:url(data:font/ttf;base64,%(hb)s) format('truetype');font-weight:700}

:root{ --ink:#2b2418; --soft:#574a3a; --rule:#3a3024; --hair:#bfae93; }
*{box-sizing:border-box}
body{margin:0;font-family:'Body',Georgia,serif;font-size:10.2pt;line-height:1.55;
     color:var(--ink);-webkit-font-smoothing:antialiased}

img.masthead{display:block;width:100%%;margin:0 0 22px}

h1{font-family:'Head',serif;font-size:17pt;margin:26px 0 10px;letter-spacing:.01em}
h2{font-family:'Head',serif;font-size:14pt;margin:26px 0 4px;letter-spacing:.02em;
   page-break-after:avoid}
h2::after{content:"";display:block;border-bottom:2.2px solid var(--rule);margin-top:5px}
h3{font-family:'Head',serif;font-size:11.6pt;margin:18px 0 4px;page-break-after:avoid}
h2+p,h2+ul,h3+p,h3+ul{margin-top:6px}

p{margin:0 0 9px}
ul,ol{margin:0 0 10px;padding-left:20px}
li{margin:0 0 5px}
li>ul{margin-top:5px}
strong{font-weight:700}
em{font-style:italic}
code{font-family:'Body',serif;font-style:italic;background:none}
hr{border:0;border-top:1.4px solid var(--hair);margin:20px 0}

@page{
  size:Letter;
  margin:14mm 16mm 19mm 16mm;
  background-color:#eeddc4;
  background-image:url(data:image/png;base64,%(tile)s);
  background-repeat:repeat;
  @bottom-left{
    content:"THE DAILY OVERFIELD \\00b7  %(folio)s";
    font-family:'Head',serif;font-size:8pt;letter-spacing:.10em;color:var(--soft);
    border-top:1.1px solid var(--rule);width:100%%;padding-top:4px;
  }
  @bottom-right{
    content:"PAGE " counter(page) " OF " counter(pages);
    font-family:'Head',serif;font-size:8pt;letter-spacing:.10em;color:var(--soft);
    border-top:1.1px solid var(--rule);width:100%%;padding-top:4px;text-align:right;
  }
}
@page:first{ @bottom-left{content:none;border:0} @bottom-right{content:none;border:0} }

blockquote{margin:0 0 10px;padding:8px 14px;border-left:3px solid var(--rule);color:var(--soft)}

table{border-collapse:collapse;width:100%%;margin:4px 0 14px;font-size:9.4pt}
th,td{text-align:left;padding:5px 9px;border-bottom:1px solid var(--hair);vertical-align:top}
th{font-family:'Head',serif;font-weight:700;border-bottom:2px solid var(--rule)}

/* keep headings with what follows, and never strand a table head */
h2,h3{break-after:avoid;break-inside:avoid}
tr,li,blockquote{break-inside:avoid}
table{break-inside:auto}
thead{break-after:avoid}
p{orphans:2;widows:2}
"""

PAGE = """<!DOCTYPE html><meta charset="utf-8"><style>%(css)s</style>
<img class="masthead" src="data:image/jpeg;base64,%(mast)s">
%(body)s
"""

def md_to_html(path):
    return subprocess.run(
        ["pandoc", "-f", "markdown+pipe_tables+hard_line_breaks", "-t", "html5", path],
        capture_output=True, text=True, check=True).stdout

MAST_PX = 2200          # ~300dpi across a 7.24in text block; the 2970px plate is
                        # ~410dpi and embeds at 6MB, which is most of the file size

def build(dt, body_md, out="briefing.pdf", keep_html=False):
    from PIL import Image
    mast = mt.build(dt, "masthead_run.png")
    im = Image.open(mast).convert("RGB")
    im = im.resize((MAST_PX, round(im.height * MAST_PX / im.width)), Image.LANCZOS)
    im = match_paper(im)
    mast = "masthead_run.jpg"
    im.save(mast, "JPEG", quality=93, subsampling=0, optimize=True)

    fonts = dict(bk=b64(f"{F}/LibreBask-400.ttf"),  bi=b64(f"{F}/LibreBask-400i.ttf"),
                 bb=b64(f"{F}/LibreBask-700.ttf"),  bbi=b64(f"{F}/LibreBask-700i.ttf"),
                 hb=b64(f"{F}/PlayfairDisplay-latin-700-normal.ttf"))

    html = PAGE % dict(css=CSS % dict(fonts, folio=mt.folio_date(dt),
                                      tile=b64(paper_tile())),
                       mast=b64(mast), body=md_to_html(body_md))
    hpath = "briefing_body.html"
    open(hpath, "w").write(html)

    from weasyprint import HTML
    HTML(string=html, base_url=".").write_pdf(out)

    if not keep_html:
        os.remove(hpath)
    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=None)
    p.add_argument("--body", required=True)
    p.add_argument("--out", default="briefing.pdf")
    a = p.parse_args()
    dt = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    print(build(dt, a.body, a.out))
