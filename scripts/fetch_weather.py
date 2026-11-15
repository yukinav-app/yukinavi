"""Fetch current weather for every resort from Open-Meteo into data/weather.json.

Runs on a schedule in GitHub Actions so the app reads one small file instead of
every visitor calling Open-Meteo directly (which hit the rate limit).
Set OPENMETEO_API_KEY (repo secret) to use the commercial endpoint.
"""
import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CHUNK = 50
UA = "YukiNavi-Weather/1.0"
JST = timezone(timedelta(hours=9))


def endpoint():
    key = os.environ.get("OPENMETEO_API_KEY")
    if key:
        return "https://customer-api.open-meteo.com/v1/forecast?", {"apikey": key}
    return "https://api.open-meteo.com/v1/forecast?", {}


def condition(code):
    if code in (71, 73, 75, 77, 85, 86): return "snow"
    if code == 0: return "clear"
    if code in (1, 2): return "sunny"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82): return "rain"
    if code in (95, 96, 99): return "storm"
    return "cloudy"


def fetch(chunk, use_elev):
    base, extra = endpoint()
    q = {
        "latitude": ",".join(str(r["lat"]) for r in chunk),
        "longitude": ",".join(str(r["lng"]) for r in chunk),
        "current": "temperature_2m,weather_code,wind_speed_10m,snow_depth",
        "daily": "snowfall_sum",
        "past_days": "1",
        "forecast_days": "7",
        "timezone": "Asia/Tokyo",
        **extra,
    }
    if use_elev:
        q["elevation"] = ",".join(str(round((r["base"] + r["top"]) / 2)) for r in chunk)
    url = base + urllib.parse.urlencode(q)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as res:
                data = json.load(res)
                return data if isinstance(data, list) else [data]
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(65)  # 分単位の上限なので1分待って再試行


def summarize(d):
    cur, sf = d["current"], (d.get("daily") or {}).get("snowfall_sum") or []
    return {
        "t": round(cur["temperature_2m"]),
        "c": condition(cur["weather_code"]),
        "w": round(cur["wind_speed_10m"]),
        "d": round((cur.get("snow_depth") or 0) * 100),
        "y": round(sf[0]) if sf and sf[0] is not None else None,
        "s7": round(sum(v or 0 for v in sf[1:])) if len(sf) > 1 else None,
        "e": round(d["elevation"]) if d.get("elevation") is not None else None,
    }


def main():
    resorts = [r for r in json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8"))
               if r.get("lat") is not None and r.get("lng") is not None]
    out, failed = {}, 0
    for use_elev in (True, False):
        group = [r for r in resorts if (r.get("base") is not None and r.get("top") is not None) == use_elev]
        for i in range(0, len(group), CHUNK):
            chunk = group[i:i + CHUNK]
            try:
                for r, d in zip(chunk, fetch(chunk, use_elev)):
                    out[r["id"]] = summarize(d)
            except Exception as e:
                failed += len(chunk)
                print("chunk failed:", e)
            time.sleep(3)
    if not out:
        raise SystemExit("no weather fetched; keeping previous file")
    json.dump({"updatedAt": datetime.now(JST).isoformat(timespec="minutes"), "wx": out},
              open(os.path.join(DATA, "weather.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"weather: {len(out)} ok, {failed} failed")


if __name__ == "__main__":
    main()
