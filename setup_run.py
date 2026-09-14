#!/usr/bin/env python3
"""
Run-start setup for THE DAILY OVERFIELD briefing PDF.

Rebuilds everything the container loses between sessions EXCEPT the plate:

  * installs WeasyPrint                      <- FIRST, so a truncated run
                                                cannot leave the renderer out
  * pulls Playfair Display and Libre Baskerville from the npm registry
    (allowlisted) and converts them to TTF

Rosewood Fill and Eastside Solid are NOT needed at run time - they are baked
into plate_template.jpg. Only the plate itself has to come from Drive.

Exits non-zero if anything the builder needs is missing, so a failed setup is
caught before any briefing work is done.

    python3 setup_run.py
"""
import importlib.util, os, subprocess, sys

FONTS = "fonts"
JOBS = [  # (npm package, file stem, output name)
    ("playfair-display",  "latin-400-normal", "PlayfairDisplay-latin-400-normal"),
    ("playfair-display",  "latin-400-italic", "PlayfairDisplay-latin-400-italic"),
    ("playfair-display",  "latin-700-normal", "PlayfairDisplay-latin-700-normal"),
    ("libre-baskerville", "latin-400-normal", "LibreBask-400"),
    ("libre-baskerville", "latin-400-italic", "LibreBask-400i"),
    ("libre-baskerville", "latin-700-normal", "LibreBask-700"),
    ("libre-baskerville", "latin-700-italic", "LibreBask-700i"),
]

def sh(*a, **k): return subprocess.run(a, check=True, capture_output=True, text=True, **k)

def have_weasyprint():
    return importlib.util.find_spec("weasyprint") is not None

def install_renderer():
    if have_weasyprint():
        print("weasyprint already present")
        return
    sh(sys.executable, "-m", "pip", "install", "weasyprint",
       "--break-system-packages", "-q")
    print("weasyprint installed")

def build_fonts():
    os.makedirs(FONTS, exist_ok=True)
    if all(os.path.exists(f"{FONTS}/{o}.ttf") for _, _, o in JOBS):
        print("fonts already present")
        return
    os.makedirs("_npm", exist_ok=True)
    sh("npm", "install", "--prefix", "_npm", "--no-audit", "--no-fund",
       "@fontsource/playfair-display", "@fontsource/libre-baskerville")
    from fontTools.ttLib import TTFont
    for pkg, stem, out in JOBS:
        src = f"_npm/node_modules/@fontsource/{pkg}/files/{pkg}-{stem}.woff"
        f = TTFont(src); f.flavor = None; f.save(f"{FONTS}/{out}.ttf")
        print("font", out)

def verify():
    problems = []
    if not have_weasyprint():
        problems.append("weasyprint NOT installed - rerun: pip install weasyprint --break-system-packages")
    missing = [o for _, _, o in JOBS if not os.path.exists(f"{FONTS}/{o}.ttf")]
    if missing:
        problems.append(f"{len(missing)} of {len(JOBS)} font faces missing: {', '.join(missing)}")
    if not os.path.exists("plate_template.jpg"):
        problems.append("plate_template.jpg missing - curl it from Drive before building")
    elif os.path.getsize("plate_template.jpg") < 500_000:
        problems.append("plate_template.jpg is too small to be the real plate - "
                        "the download probably returned an HTML page, not a JPEG")
    return problems

def main():
    install_renderer()   # cheapest and most fragile step goes first
    build_fonts()
    problems = verify()
    if problems:
        print("SETUP INCOMPLETE - do not build:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("ready - renderer, all 7 font faces and plate confirmed")

if __name__ == "__main__":
    main()
