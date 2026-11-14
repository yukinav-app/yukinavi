"""Merge researched batch outputs (data/batches/out_*.json) into the app data.

- status "open"   -> added to data/resorts.json (detailed resorts)
- status "closed" -> removed from data/resorts_all.json (map no longer shows it)
- status "unknown"-> left as a name-only pin in data/resorts_all.json
"""
import glob, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

HUBS = {
    "札幌": (43.0618, 141.3545), "旭川": (43.7709, 142.3650), "函館": (41.7687, 140.7288),
    "帯広": (42.9236, 143.1966), "釧路": (42.9849, 144.3820), "青森": (40.8244, 140.7400),
    "盛岡": (39.7036, 141.1527), "秋田": (39.7186, 140.1024), "仙台": (38.2682, 140.8694),
    "山形": (38.2404, 140.3633), "福島": (37.7608, 140.4747), "宇都宮": (36.5551, 139.8828),
    "前橋": (36.3895, 139.0634), "東京": (35.6812, 139.7671), "新潟": (37.9161, 139.0364),
    "上越妙高": (37.0745, 138.2367), "長野": (36.6433, 138.1886), "松本": (36.2380, 137.9720),
    "富山": (36.6953, 137.2113), "金沢": (36.5780, 136.6480), "福井": (36.0641, 136.2196),
    "名古屋": (35.1709, 136.8815), "大阪": (34.7025, 135.4959), "広島": (34.3976, 132.4754),
    "岡山": (34.6655, 133.9177), "鳥取": (35.4936, 134.2259), "松江": (35.4646, 133.0635),
    "松山": (33.8392, 132.7650), "高知": (33.5672, 133.5435), "福岡": (33.5902, 130.4207),
    "熊本": (32.7898, 130.6886), "大分": (33.2382, 131.6126), "宮崎": (31.9156, 131.4320),
}
ROAD_FACTOR = 1.25  # straight-line km -> rough road km

FIELDS = ["id", "lat", "lng", "nameJa", "nameEn", "prefJa", "prefEn", "region", "cityJa", "cityEn",
          "distKm", "timeJa", "timeEn", "accessJa", "accessEn", "flight", "base", "top", "courses", "lifts",
          "terrain", "liftAdult", "liftStudent", "priceSeason", "english", "descJa", "descEn", "status"]


def km(a, b):
    r = 6371
    dlat, dlng = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def norm(name):
    return re.sub(r"(スキー場|スノーパーク|\s|・)", "", name or "")


def slug(s):
    return re.sub(r"[^a-z0-9_]", "", (s or "").lower().replace("-", "_").replace(" ", "_"))


def main():
    resorts = json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8"))
    allr = json.load(open(os.path.join(DATA, "resorts_all.json"), encoding="utf-8"))
    ids = {r["id"] for r in resorts}
    merged_keys = {r.get("srcKey") for r in resorts if r.get("srcKey")}
    _ov = os.path.join(DATA, "merge_overrides.json")
    excluded = set(json.load(open(_ov, encoding="utf-8")).get("exclude", [])) if os.path.exists(_ov) else set()
    closed_keys, added, unknown, problems = set(), 0, 0, []

    for path in sorted(glob.glob(os.path.join(DATA, "batches", "out_*.json"))):
        for x in json.load(open(path, encoding="utf-8")):
            st = x.get("status")
            if st in ("closed", "notski", "merged"):
                closed_keys.add(x.get("key"))
                continue
            if x.get("key") in merged_keys or x.get("key") in excluded:
                continue
            if st != "open":
                unknown += 1
                continue
            if x.get("lat") is None or x.get("lng") is None:
                problems.append(f"no coords: {x.get('nameJa')}")
                continue
            city = x.get("cityJa")
            if city not in HUBS:
                problems.append(f"unknown hub {city}: {x.get('nameJa')}")
                continue
            dup = next((e for e in resorts if norm(e["nameJa"]) == norm(x.get("nameJa")) or
                        (e.get("lat") is not None and km((e["lat"], e["lng"]), (x["lat"], x["lng"])) < 0.3)), None)
            if dup:
                # 既に詳細データがあるスキー場と同じ場所：簡易ピンだけ外す
                closed_keys.add(x.get("key"))
                problems.append(f"duplicate of existing {dup['nameJa']}: {x.get('nameJa')} (pin removed)")
                continue
            r = {k: x.get(k) for k in FIELDS}
            base_id = slug(x.get("id")) or slug(x.get("nameEn")) or x["key"]
            rid, n = base_id, 2
            while rid in ids:
                rid, n = f"{base_id}_{n}", n + 1
            r["id"] = rid
            ids.add(rid)
            r["distKm"] = round(km(HUBS[city], (r["lat"], r["lng"])) * ROAD_FACTOR)
            r["flight"] = False
            r["status"] = "open"
            r["srcKey"] = x["key"]
            resorts.append(r)
            added += 1

    ov_path = os.path.join(DATA, "merge_overrides.json")
    if os.path.exists(ov_path):
        ov = json.load(open(ov_path, encoding="utf-8"))
        excl = set(ov.get("exclude", []))
        resorts = [r for r in resorts if r.get("srcKey") not in excl]
        closed_keys |= excl
        for rid, (lat, lng) in ov.get("coords", {}).items():
            for r in resorts:
                if r["id"] == rid:
                    r["lat"], r["lng"] = lat, lng

    # 閉鎖・スキー不可は地図から外し、詳細データ化したものは簡易ピンを二重に出さない
    detailed_keys = {r.get("srcKey") for r in resorts if r.get("srcKey")}
    allr = [a for a in allr if a.get("key") not in closed_keys and a.get("key") not in detailed_keys]

    json.dump(resorts, open(os.path.join(DATA, "resorts.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(allr, open(os.path.join(DATA, "resorts_all.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"added {added}, closed/notski {len(closed_keys)}, unknown {unknown}, total detailed {len(resorts)}, name-only pins {len(allr)}")
    for p in problems:
        print("WARN", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
