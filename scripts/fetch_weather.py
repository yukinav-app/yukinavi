"""Fetch weather for every resort from MET Norway (api.met.no) into data/weather.json.

Runs on a schedule in GitHub Actions so the app reads one small file instead of
every visitor calling a weather API. MET Norway data is CC BY 4.0 and may be used
commercially with attribution (https://api.met.no/doc/TermsOfService).
Values are shown as MET Norway publishes them; we only pick and count, we do not
make our own forecast (snow days = days whose 6-hour symbol is a snow symbol).
"""
import json, os, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "YukiNavi/1.0 https://yukinavi-app.github.io/yukinavi/"  # MET Norwayの規約：アプリ名と連絡先（サイト）を名乗る
URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lng:.4f}{alt}"
JST = timezone(timedelta(hours=9))


def condition(symbol):
    s = symbol or ""
    if "thunder" in s: return "storm"
    if "snow" in s: return "snow"
    if "sleet" in s: return "sleet"
    if "rain" in s: return "rain"
    if s.startswith("clearsky"): return "clear"
    if s.startswith("fair"): return "sunny"
    if s.startswith("partlycloudy"): return "partly"
    if s.startswith("fog"): return "fog"
    return "cloudy"


def fetch(r, alt):
    url = URL.format(lat=r["lat"], lng=r["lng"], alt=f"&altitude={alt}" if alt is not None else "")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))


def summarize(d, alt):
    ts = d["properties"]["timeseries"]
    now = ts[0]["data"]
    det = now["instant"]["details"]
    sym = (now.get("next_1_hours") or now.get("next_6_hours") or {}).get("summary", {}).get("symbol_code")
    today = datetime.now(JST).date()
    days = [today + timedelta(days=i) for i in range(7)]
    snow = set()
    for e in ts:
        t = datetime.fromisoformat(e["time"].replace("Z", "+00:00"))
        s6 = (e["data"].get("next_6_hours") or {}).get("summary", {}).get("symbol_code")
        if t.hour % 6 == 0 and s6 and "snow" in s6:
            snow.add(t.astimezone(JST).date())
    return {
        "t": round(det["air_temperature"]),
        "c": condition(sym),
        "w": round(det["wind_speed"] * 3.6),
        "sd": sum(1 for day in days if day in snow),
        "e": alt,
    }


def main():
    resorts = [r for r in json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8"))
               if r.get("lat") is not None and r.get("lng") is not None]
    def one(r):
        alt = round((r["base"] + r["top"]) / 2) if r.get("base") is not None and r.get("top") is not None else None
        try:
            return r["id"], summarize(fetch(r, alt), alt)
        except Exception as e:
            print("failed:", r["id"], e)
            return r["id"], None
    # 4並列（1件約1秒なので毎秒4回前後。規約の上限 毎秒20回より十分少ない）
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(one, resorts))
    out = {k: v for k, v in results if v}
    failed = len(resorts) - len(out)
    if len(out) < len(resorts) * 0.8:
        raise SystemExit(f"only {len(out)}/{len(resorts)} fetched; keeping previous file")
    json.dump({"updatedAt": datetime.now(JST).isoformat(timespec="minutes"), "source": "MET Norway", "wx": out},
              open(os.path.join(DATA, "weather.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"weather: {len(out)} ok, {failed} failed")


if __name__ == "__main__":
    main()
