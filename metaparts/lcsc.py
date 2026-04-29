import csv
import json
import re
import uuid
from pathlib import Path

INPUT = Path("lcsc.csv")
OUTPUT = Path("lcsc.json")

RE_RES = re.compile(r'(\d+(?:\.\d+)?\s*[kKmM]?(?:\s*(?:ohm|Ω))?)', re.I)
RE_CAP = re.compile(r'(\d+(?:\.\d+)?\s*(?:uF|µF|nF|pF|uf|nf|pf))', re.I)
RE_TOL = re.compile(r'(\d+(?:\.\d+)?\s*%)')
RE_VOLT = re.compile(r'(\d+(?:\.\d+)?\s*V)', re.I)
RE_POWER = re.compile(r'(\d+(?:\.\d+)?\s*(?:mW|W))', re.I)
RE_FOOT = re.compile(r'\b(0201|0402|0603|0805|1206)\b')
RE_DIE = re.compile(r'\b(X7R|X5R|C0G|NP0|X7S|Y5V)\b', re.I)

def partsbox_id_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r'/([A-Za-z0-9]{20,40})(?:[/?#]|$)', url)
    if m:
        print(m.group(1))
        return m.group(1)
    return None

def norm_res(s: str) -> str:
    s = s.replace('Ω', 'ohm')
    s = s.lower().replace('ohm', '').strip()
    s = s.replace(' ', '')
    return s

def norm_cap(s: str) -> str:
    s = s.replace('µ', 'u').replace('µf', 'uF')
    s = s.replace(' ', '')
    # ensure unit case like "nF"
    return re.sub(r'([unp]?)f$', lambda m: m.group(0).upper(), s, flags=re.I)

def norm_power(s: str) -> str:
    s = s.strip().lower()
    if s.endswith('mw'):
        try:
            mw = float(s[:-2])
            w = mw / 1000.0
            return f"{w:.3f}W".rstrip('0').rstrip('.') + "W" if False else f"{w}W"
        except Exception:
            return s
    return s.upper()

def detect_type(desc: str, name: str, mpn: str) -> str:
    txt = " ".join([desc or "", name or "", mpn or ""]).lower()
    if re.search(r'\bresistor\b|\brockwell\b|\bohm\b|\bohm\b|\bohm\b|ohm\b', txt) or 'res' in txt:
        return "resistor"
    if re.search(r'\bcapacitor\b|\bcapacit(?:or|ance)\b|\buF\b|\bnF\b|\bpF\b', txt, re.I):
        return "capacitor"
    return ""

rows = []
with INPUT.open(newline='', encoding='utf-8') as fh:
    reader = csv.DictReader(fh)
    for r in reader:
        name = r.get("Name", "").strip()
        desc = r.get("Description", "").strip()
        footprint = r.get("Footprint", "").strip()
        mpn = r.get("MPN", "").strip() or name

        ptype = detect_type(desc, name, mpn)
        if ptype not in ("resistor", "capacitor"):
            continue

        specs = {"type": ptype}

        # footprint
        if footprint:
            specs["footprint"] = footprint
        else:
            m = RE_FOOT.search(desc)
            if m:
                specs["footprint"] = m.group(1)

        if ptype == "resistor":
            m = RE_RES.search(desc)
            if m:
                specs["resistance"] = norm_res(m.group(1))
            tol = RE_TOL.search(desc)
            if tol:
                specs["tolerance"] = tol.group(1).replace(' ', '')
            pwr = RE_POWER.search(desc)
            if pwr:
                specs["power_rating"] = pwr.group(1).replace(' ', '')
        else:  # capacitor
            m = RE_CAP.search(desc)
            if m:
                specs["capacitance"] = norm_cap(m.group(1))
            tol = RE_TOL.search(desc)
            if tol:
                specs["tolerance"] = tol.group(1).replace(' ', '')
            volt = RE_VOLT.search(desc)
            if volt:
                specs["voltage_rating"] = volt.group(1).replace(' ', '').upper()
            die = RE_DIE.search(desc)
            if die:
                specs["dielectric"] = die.group(1).upper()

        url = r.get("URL").strip()
        pb_id = partsbox_id_from_url(url)

        entry = {
            "part/id": pb_id,
            "specs": specs,
            "part/description": desc or name,
            "part/mpn": mpn,
        }
        rows.append(entry)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", encoding="utf-8") as out:
    json.dump(rows, out, indent=2, ensure_ascii=False)

print(f"Wrote {len(rows)} entries to {OUTPUT}")