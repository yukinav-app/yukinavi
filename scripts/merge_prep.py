"""Merge trip-prep research (data/batches_v2/out_*.json) into data/resorts.json.

Adds rental / school / ticket / transit objects to each resort. Only non-empty
research results overwrite; safe to re-run.
"""
import glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def has_value(obj):
    return isinstance(obj, dict) and any(v is not None for v in obj.values())


def main():
    resorts = json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8"))
    by_id = {r["id"]: r for r in resorts}
    merged, missing = 0, []
    for path in sorted(glob.glob(os.path.join(DATA, "batches_v2", "out_*.json"))):
        for x in json.load(open(path, encoding="utf-8")):
            r = by_id.get(x.get("id"))
            if not r:
                missing.append(x.get("id"))
                continue
            for k in ("rental", "school", "ticket", "transit"):
                if has_value(x.get(k)):
                    r[k] = x[k]
            if x.get("winterClosed"):
                r["winterClosed"] = True
            merged += 1
    json.dump(resorts, open(os.path.join(DATA, "resorts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    def count(k, f):
        return sum(1 for r in resorts if isinstance(r.get(k), dict) and f(r[k]))
    print(f"merged {merged} | rental {count('rental', lambda v: v.get('available') is not None)}"
          f" | school {count('school', lambda v: v.get('available') is not None)}"
          f" | onlineTicket {count('ticket', lambda v: bool(v.get('onlineUrl')))}"
          f" | transit {count('transit', lambda v: v.get('byPublic') is not None)}"
          f" | winterClosed {sum(1 for r in resorts if r.get('winterClosed'))}")
    if missing:
        print("WARN unknown ids:", missing)


if __name__ == "__main__":
    main()
