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


def slug(s):
    return re.sub(r"[^a-z0-9_]", "", (s or "").lower().replace("-", "_").replace(" ", "_"))


def main():
    resorts = json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8"))
    allr = json.load(open(os.path.join(DATA, "resorts_all.json"), encoding="utf-8"))
    ids = {r["id"] for r in resorts}
    merged_keys = {r.get("srcKey") for r in resorts if r.get("srcKey")}
    closed_names, added, unknown, problems = set(), 0, 0, []

    for path in sorted(glob.glob(os.path.join(DATA, "batches", "out_*.json"))):
        for x in json.load(open(path, encoding="utf-8")):
            st = x.get("status")
            if st == "closed":
                closed_names.add((x.get("nameJa"), x.get("prefJa")))
                continue
            if x.get("key") in merged_keys:
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

    if closed_names:
        allr = [a for a in allr if (a["name"], a["pref"]) not in closed_names]

    json.dump(resorts, open(os.path.join(DATA, "resorts.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(allr, open(os.path.join(DATA, "resorts_all.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"added {added}, closed removed {len(closed_names)}, unknown {unknown}, total detailed {len(resorts)}")
    for p in problems:
        print("WARN", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
