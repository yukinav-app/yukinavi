"""Merge 2026-27 opening/closing dates (data/batches_open/out_*.json) into data/resorts.json.

The app shows openDate only while it is still in the future. Safe to re-run.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DATE = re.compile(r"^2026-(1[0-2])-\d{2}$|^2027-0[1-5]-\d{2}$")  # 2026-27シーズンの範囲外は捨てる
CLOSE = re.compile(r"^2027-0[1-6]-\d{2}$")


def main():
    resorts = json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8"))
    by_id = {r["id"]: r for r in resorts}
    merged, rejected, missing = 0, [], []
    for path in sorted(glob.glob(os.path.join(DATA, "batches_open", "out_*.json"))):
        for x in json.load(open(path, encoding="utf-8")):
            r = by_id.get(x.get("id"))
            if not r:
                missing.append(x.get("id"))
                continue
            od, cd = x.get("openDate"), x.get("closeDate")
            if od and not DATE.match(od):
                rejected.append(f"{x['id']} openDate {od}")
                od = None
            if cd and not CLOSE.match(cd):
                rejected.append(f"{x['id']} closeDate {cd}")
                cd = None
            r["openDate"], r["closeDate"] = od, cd
            r["openNote"] = (x.get("openNote") or None) if not od else None
            r["alreadyOpen"] = True if x.get("alreadyOpen") else None
            r["openSource"] = x.get("sourceUrl")
            merged += 1
    json.dump(resorts, open(os.path.join(DATA, "resorts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"merged {merged} | openDate {sum(1 for r in resorts if r.get('openDate'))}"
          f" | noteOnly {sum(1 for r in resorts if r.get('openNote'))}"
          f" | alreadyOpen {sum(1 for r in resorts if r.get('alreadyOpen'))}")
    for x in rejected:
        print("REJECTED", x)
    if missing:
        print("WARN unknown ids:", missing)


if __name__ == "__main__":
    main()
