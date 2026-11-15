"""Generate static, search-engine-readable pages from data/resorts.json.

Outputs (Japanese / English):
  r/<id>/index.html, en/r/<id>/index.html        one page per resort
  r/index.html, en/r/index.html                  prefecture-grouped list
  sitemap.xml, robots.txt
Re-run after any data change. The site URL lives in data/site.json.
"""
import html, json, os, shutil
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = json.load(open(os.path.join(DATA, "site.json"), encoding="utf-8"))
BASE = SITE["baseUrl"].rstrip("/")

PREF_ORDER = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県",
              "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県",
              "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県",
              "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県",
              "宮崎県", "鹿児島県", "沖縄県"]

T = {
    "ja": {
        "lang": "ja", "title": "{name}（{pref}）リフト券料金・コース・アクセス｜YukiNavi",
        "desc": "{name}（{pref}）の{season}大人1日券{price}、標高{elev}、{courses}。{text}",
        "adult": "大人1日券", "student": "学生・ユース", "free": "無料", "elev": "標高（麓〜山頂）", "runs": "コース数",
        "lifts": "リフト数", "access": "アクセス", "terrain": "コース難易度", "beg": "初級", "int": "中級", "adv": "上級",
        "english": "英語対応", "en": {"high": "高い", "medium": "あり", "low": "限定的"}, "official": "公式サイト",
        "maps": "Googleマップで見る", "cta": "YukiNaviで天気・7日間の降雪予報を見る", "same": "{pref}のほかのスキー場",
        "checked": "掲載情報の確認日：{d}。料金・営業状況は変わることがあります。お出かけ前に公式サイトでご確認ください。",
        "na": "—", "list_title": "全国のスキー場一覧（都道府県別）｜YukiNavi",
        "list_desc": "日本全国{n}か所のスキー場の2026-27シーズンのリフト券料金・コース数・アクセスを都道府県別にまとめました。",
        "list_h1": "全国のスキー場一覧", "home": "YukiNavi トップ", "all": "全国のスキー場一覧",
        "runs_n": "{n}コース", "lifts_n": "{n}基", "season": "（{s}シーズン）",
    },
    "en": {
        "lang": "en", "title": "{name} ({pref}) lift pass price, runs & access | YukiNavi",
        "desc": "{name} in {pref}, Japan: {season}adult day pass {price}, elevation {elev}, {courses}. {text}",
        "adult": "Adult day pass", "student": "Student / youth", "free": "Free", "elev": "Elevation (base–top)", "runs": "Runs",
        "lifts": "Lifts", "access": "Access", "terrain": "Terrain", "beg": "Beginner", "int": "Intermediate",
        "adv": "Advanced", "english": "English support", "en": {"high": "Good", "medium": "Some", "low": "Limited"},
        "official": "Official site", "maps": "Open in Google Maps",
        "cta": "See weather and 7-day snowfall on YukiNavi", "same": "More ski resorts in {pref}",
        "checked": "Info last checked: {d}. Prices and operating status can change; check the official site before you go.",
        "na": "—", "list_title": "All ski resorts in Japan by prefecture | YukiNavi",
        "list_desc": "Lift pass prices, runs and access for {n} ski resorts across Japan for the 2026-27 season, by prefecture.",
        "list_h1": "Ski resorts in Japan", "home": "YukiNavi home", "all": "All ski resorts in Japan",
        "runs_n": "{n} runs", "lifts_n": "{n} lifts", "season": "{s} ",
    },
}

CSS = """*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;background:#EEF1F4;color:#1C2430;line-height:1.6}
a{color:#1F3550}.wrap{max-width:760px;margin:0 auto;padding:16px}header{background:#1F3550;color:#fff}header a{color:#fff;text-decoration:none;font-weight:700;letter-spacing:.3px}
.crumb{font-size:12px;color:#5B6672;margin:6px 0 2px}.crumb a{color:#5B6672}h1{font-size:26px;line-height:1.25;margin:4px 0 6px}.sub{color:#5B6672;font-size:13px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}.box{background:#fff;border:1px solid #D7DEE5;border-radius:12px;padding:12px}
.box b{display:block;font-size:20px}.box span{font-size:12px;color:#5B6672}.bar{display:flex;height:10px;border-radius:99px;overflow:hidden;margin:6px 0}
.legend{font-size:12px;color:#5B6672}.cta{display:block;text-align:center;background:#E2792B;color:#fff;font-weight:700;text-decoration:none;border-radius:12px;padding:14px;margin:18px 0}
.links a{display:inline-block;margin:0 14px 8px 0}.note{font-size:12px;color:#5B6672;border-top:1px solid #D7DEE5;padding-top:12px;margin-top:20px}
ul.list{list-style:none;padding:0;columns:2;font-size:14px}ul.list li{margin:3px 0;break-inside:avoid}h2{font-size:18px;margin:22px 0 8px}
.lang{float:right;font-size:12px}"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def yen(v, L):
    return T[L]["free"] if v == 0 else f"¥{v:,}"


def page_url(L, rid):
    return f"{BASE}/{'en/' if L == 'en' else ''}r/{rid}/"


def head(L, title, desc, canonical, alt_ja, alt_en, jsonld=None):
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html><html lang="{L}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{alt_ja}"><link rel="alternate" hreflang="en" href="{alt_en}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}"><meta property="og:site_name" content="YukiNavi"><meta name="twitter:card" content="summary">
<link rel="icon" href="{BASE}/icons/icon-192.png"><style>{CSS}</style>{ld}</head><body>
<header><div class="wrap"><a href="{BASE}/">YukiNavi</a></div></header><main class="wrap">"""


def resort_page(r, L, same_pref):
    t = T[L]
    ja = L == "ja"
    name = r["nameJa"] if ja else (r.get("nameEn") or r["nameJa"])
    pref = r["prefJa"] if ja else (r.get("prefEn") or r["prefJa"])
    text = (r.get("descJa") if ja else r.get("descEn")) or ""
    access = r.get("accessJa") if ja else (r.get("accessEn") or r.get("accessJa"))
    if not access and r.get("timeJa"):
        access = f"{r['cityJa']}から {r['timeJa']}" if ja else f"{r.get('timeEn') or r['timeJa']} from {r.get('cityEn') or r['cityJa']}"
    season = t["season"].format(s=r["priceSeason"]) if r.get("priceSeason") else ""
    price = yen(r["liftAdult"], L) if r.get("liftAdult") is not None else t["na"]
    elev = f"{r['base']}–{r['top']}m" if r.get("base") is not None and r.get("top") is not None else t["na"]
    courses = t["runs_n"].format(n=r["courses"]) if r.get("courses") is not None else t["runs"] + " " + t["na"]
    desc = t["desc"].format(name=name, pref=pref, season=season, price=price, elev=elev, courses=courses, text=text)[:160]
    url_ja, url_en = page_url("ja", r["id"]), page_url("en", r["id"])
    jsonld = {"@context": "https://schema.org", "@type": "SkiResort", "name": name,
              "address": {"@type": "PostalAddress", "addressRegion": pref, "addressCountry": "JP"},
              "url": page_url(L, r["id"])}
    if r.get("lat") is not None:
        jsonld["geo"] = {"@type": "GeoCoordinates", "latitude": r["lat"], "longitude": r["lng"]}
    if r.get("officialUrl"):
        jsonld["sameAs"] = r["officialUrl"]

    boxes = [(price, t["adult"] + (f" ({r['priceSeason']})" if r.get("priceSeason") else ""))]
    if r.get("liftStudent") is not None:
        boxes.append((yen(r["liftStudent"], L), t["student"]))
    boxes.append((elev, t["elev"]))
    if r.get("courses") is not None:
        boxes.append((t["runs_n"].format(n=r["courses"]), t["runs"]))
    if r.get("lifts") is not None:
        boxes.append((t["lifts_n"].format(n=r["lifts"]), t["lifts"]))
    boxes.append((t["en"].get(r.get("english"), t["na"]), t["english"]))
    grid = "".join(f'<div class="box"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for v, k in boxes)

    terrain = ""
    if r.get("terrain"):
        b, i, a = r["terrain"]
        terrain = (f'<h2>{t["terrain"]}</h2><div class="bar"><div style="width:{b}%;background:#2F8F5B"></div>'
                   f'<div style="width:{i}%;background:#2E6B8A"></div><div style="width:{a}%;background:#E2792B"></div></div>'
                   f'<div class="legend">{t["beg"]} {b}% ・ {t["int"]} {i}% ・ {t["adv"]} {a}%</div>')

    links = []
    if r.get("officialUrl"):
        links.append(f'<a href="{esc(r["officialUrl"])}" rel="noopener" target="_blank">{t["official"]}</a>')
    from urllib.parse import quote
    links.append(f'<a href="https://www.google.com/maps/search/?api=1&query={quote(r["nameJa"])}" rel="noopener" target="_blank">{t["maps"]}</a>')

    others = "".join(
        f'<li><a href="{page_url(L, o["id"])}">{esc(o["nameJa"] if ja else (o.get("nameEn") or o["nameJa"]))}</a></li>'
        for o in same_pref if o["id"] != r["id"])
    app_link = f"{BASE}/?r={r['id']}" + ("&lang=en" if not ja else "")
    other_lang = f'<a class="lang" href="{url_en if ja else url_ja}">{"English" if ja else "日本語"}</a>'

    return (head(L, t["title"].format(name=name, pref=pref), desc, page_url(L, r["id"]), url_ja, url_en, jsonld)
            + f'{other_lang}<div class="crumb"><a href="{BASE}/{"en/" if not ja else ""}r/">{t["all"]}</a> › {esc(pref)}</div>'
            + f'<h1>{esc(name)}</h1><div class="sub">{esc(pref)}{" ・ " + esc(access) if access else ""}</div>'
            + (f"<p>{esc(text)}</p>" if text else "")
            + f'<div class="grid">{grid}</div>{terrain}'
            + f'<a class="cta" href="{app_link}">{t["cta"]}</a>'
            + (f'<h2>{t["access"]}</h2><p>{esc(access)}</p>' if access else "")
            + f'<div class="links">{"".join(links)}</div>'
            + (f'<h2>{esc(t["same"].format(pref=pref))}</h2><ul class="list">{others}</ul>' if others else "")
            + f'<div class="note">{esc(t["checked"].format(d=r.get("checkedAt", "")))}</div>'
            + "</main></body></html>")


def list_page(L, by_pref, n):
    t = T[L]
    ja = L == "ja"
    body = ""
    for pref, rs in by_pref.items():
        label = pref if ja else (rs[0].get("prefEn") or pref)
        items = "".join(
            f'<li><a href="{page_url(L, r["id"])}">{esc(r["nameJa"] if ja else (r.get("nameEn") or r["nameJa"]))}</a>'
            f'{" — " + yen(r["liftAdult"], L) if r.get("liftAdult") is not None else ""}</li>' for r in rs)
        body += f"<h2>{esc(label)}（{len(rs)}）</h2><ul class=\"list\">{items}</ul>" if ja else \
            f"<h2>{esc(label)} ({len(rs)})</h2><ul class=\"list\">{items}</ul>"
    url_ja, url_en = f"{BASE}/r/", f"{BASE}/en/r/"
    other = f'<a class="lang" href="{url_en if ja else url_ja}">{"English" if ja else "日本語"}</a>'
    return (head(L, t["list_title"], t["list_desc"].format(n=n), url_ja if ja else url_en, url_ja, url_en)
            + f'{other}<h1>{t["list_h1"]}</h1><p>{esc(t["list_desc"].format(n=n))}</p>{body}</main></body></html>')


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)


def main():
    resorts = [r for r in json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8")) if r.get("status") != "closed"]
    by_pref = OrderedDict((p, []) for p in PREF_ORDER)
    for r in resorts:
        by_pref.setdefault(r["prefJa"], []).append(r)
    by_pref = OrderedDict((p, sorted(rs, key=lambda x: x["nameJa"])) for p, rs in by_pref.items() if rs)

    for d in ("r", os.path.join("en", "r")):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    urls = [f"{BASE}/", f"{BASE}/r/", f"{BASE}/en/r/"]
    for pref, rs in by_pref.items():
        for r in rs:
            for L in ("ja", "en"):
                sub = "r" if L == "ja" else os.path.join("en", "r")
                write(os.path.join(ROOT, sub, r["id"], "index.html"), resort_page(r, L, rs))
                urls.append(page_url(L, r["id"]))
    write(os.path.join(ROOT, "r", "index.html"), list_page("ja", by_pref, len(resorts)))
    write(os.path.join(ROOT, "en", "r", "index.html"), list_page("en", by_pref, len(resorts)))

    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    write(os.path.join(ROOT, "sitemap.xml"),
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
    write(os.path.join(ROOT, "robots.txt"), f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"pages: {len(resorts) * 2} resort pages + 2 lists, sitemap {len(urls)} urls, base {BASE}")


if __name__ == "__main__":
    main()
