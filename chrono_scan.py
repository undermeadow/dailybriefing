#!/usr/bin/env python3
"""
THE DAILY OVERFIELD - Nina Simone Rev 2 chronology scanner.

Reads 2-Nina_Simone_Performance_Chronology.pdf (already downloaded by the prep
step), and prints ONLY the entries that touch today or the next N days, so the
40-page PDF never has to enter the conversation.

    python3 chrono_scan.py --pdf rev2.pdf              # today + 7 days
    python3 chrono_scan.py --pdf rev2.pdf --date 2026-09-16 --days 7

Three kinds of match are reported, each labelled:
    DATE       an entry whose header is a single day
    RANGE      an entry whose header is a day range spanning a target day
    ITINERARY  a "Sept 19: Venue" stop inside a tour or residency body
Month-only and year-only entries are never matched: they cannot be "on this day".
"""
import argparse, datetime, re, subprocess

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
ABBR = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "june": 6,
        "jul": 7, "july": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
MON = "(" + "|".join(sorted(list(MONTHS) + list(ABBR), key=len, reverse=True)) + ")"
DASH = r"\s*[\u2013\u2014-]\s*"

HEAD = re.compile(r"^(%s)\b.*?\b(\d{4})\b.*\u2014" % MON[1:-1], re.I)
SINGLE = re.compile(r"^%s\.?\s+(\d{1,2}),\s*(\d{4})" % MON, re.I)
SAME_MONTH_RANGE = re.compile(r"^%s\.?\s+(\d{1,2})%s(\d{1,2}),\s*(\d{4})" % (MON, DASH), re.I)
CROSS_MONTH_RANGE = re.compile(r"^%s\.?\s+(\d{1,2})%s%s\.?\s+(\d{1,2}),\s*(\d{4})" % (MON, DASH, MON), re.I)
STOP = re.compile(r"%s\.?\s+(\d{1,2}):\s*([^\u00b7]+)" % MON, re.I)

def mnum(s):
    s = s.lower().rstrip(".")
    return MONTHS.get(s) or ABBR.get(s)

def entries(text):
    cur = None
    for line in text.splitlines():
        if HEAD.match(line.strip()) and not line.startswith(" "):
            if cur: yield cur
            cur = [line.strip(), []]
        elif cur is not None:
            cur[1].append(line.strip())
    if cur: yield cur

def span(m1, d1, m2, d2, y):
    a = datetime.date(y, m1, d1); b = datetime.date(y if m2 >= m1 else y + 1, m2, d2)
    while a <= b:
        yield a
        a += datetime.timedelta(days=1)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", default="rev2.pdf")
    p.add_argument("--date", default=None)
    p.add_argument("--days", type=int, default=7)
    a = p.parse_args()
    today = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    want = {(today + datetime.timedelta(days=i)).strftime("%m%d"): i for i in range(a.days + 1)}

    text = subprocess.run(["pdftotext", "-layout", a.pdf, "-"],
                          capture_output=True, text=True, check=True).stdout
    hits = []
    for head, body in entries(text):
        first = next((b for b in body if b), "")
        m = CROSS_MONTH_RANGE.match(head)
        if m:
            days = list(span(mnum(m[1]), int(m[2]), mnum(m[3]), int(m[4]), int(m[5])))
            kind = "RANGE"
        elif (m := SAME_MONTH_RANGE.match(head)):
            days = list(span(mnum(m[1]), int(m[2]), mnum(m[1]), int(m[3]), int(m[4])))
            kind = "RANGE"
        elif (m := SINGLE.match(head)):
            days = [datetime.date(int(m[3]), mnum(m[1]), int(m[2]))]
            kind = "DATE"
        else:
            days, kind = [], None
        inwin = [d for d in days if d.strftime("%m%d") in want]
        if inwin:
            d0 = inwin[0]; k = d0.strftime("%m%d")
            note = ""
            if kind == "RANGE":
                note = "spans %s..%s of window" % (
                    "TODAY" if want[k] == 0 else "+%d" % want[k],
                    "+%d" % want[inwin[-1].strftime("%m%d")])
            hits.append((want[k], k, d0.year, kind, head, first, note))
        year = int(re.search(r"\b(\d{4})\b", head)[1])
        body_txt = " ".join(body)
        for s in STOP.finditer(body_txt):
            mo = mnum(s[1])
            if not mo: continue
            k = "%02d%02d" % (mo, int(s[2]))
            if k in want:
                hits.append((want[k], k, year, "ITINERARY", head, first, s[3].strip(" .")))
    seen = set()
    print("REV2 SCAN %s +%d days" % (today.isoformat(), a.days))
    for off, k, y, kind, head, first, stop in sorted(hits):
        key = (k, y, kind, head, stop)
        if key in seen: continue
        seen.add(key)
        tag = "TODAY" if off == 0 else "+%d" % off
        line = "%s %s %d %s | %s | %s" % (tag, k, y, kind, head, first)
        if stop: line += (" | " if kind == "RANGE" else " | stop: ") + stop
        print(line)
    if not hits:
        print("no day-level entries in window")

if __name__ == "__main__":
    main()
