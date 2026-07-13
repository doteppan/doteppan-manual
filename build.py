#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
どてっぱん マニュアル動画一覧ページ 自動生成スクリプト

Googleスプレッドシート(マニュアル動画リスト)をCSVで取得し、
index.html を生成する。GitHub Actions から毎朝9時(日本時間)に実行される。
"""
import csv
import html
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

SHEET_ID = "1BjoGye1CwqZ9RGCx0HyvW3em4Cs3hAhAWqoEpWNxwYI"
GID = "1386834576"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

JST = timezone(timedelta(hours=9))

# 表記の統一ルール(シート上の表記 → ページ上の表記)
NORMALIZE = {
    "ウマチャ": "UMACHA",
}

# タイトルからカテゴリを推定するルール(シート側にカテゴリ列ができたらそちらを優先)
CATEGORY_RULES = [
    ("調理", ["焼き方", "作り方", "仕込み", "作成", "出汁", "ドロ", "ソース"]),
    ("接客", ["お出迎え", "お見送り", "配膳", "ご案内", "オーダー", "メニュー説明",
              "電話", "ホール", "クチコミ", "声掛け", "お客"]),
    ("清掃・準備", ["清掃", "リセット", "アイドル", "身だしなみ"]),
]


def categorize(title):
    for name, keywords in CATEGORY_RULES:
        if any(k in title for k in keywords):
            return name
    return "その他"


def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|watch\?v=|embed/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None


def fetch_rows():
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        text = res.read().decode("utf-8")
    return list(csv.reader(io.StringIO(text)))


def parse(rows):
    videos, upcoming = [], []
    header_seen = False
    for row in rows:
        row = [c.strip() for c in row] + [""] * (5 - len(row))
        if not header_seen:
            if row[0] == "No":
                header_seen = True
            continue
        no, uploaded, date, title, url = row[:5]
        if not title:
            continue
        for before, after in NORMALIZE.items():
            title = title.replace(before, after)
        if uploaded.upper() == "TRUE" and url:
            vid = youtube_id(url)
            if not vid:
                print(f"注意: No.{no}「{title}」のURLからYouTube IDを取得できませんでした: {url}")
                continue
            videos.append({
                "no": no, "date": date, "title": title,
                "url": url.split("?")[0], "id": vid,
                "category": categorize(title),
            })
        else:
            upcoming.append({"no": no, "title": title})
    return videos, upcoming


def esc(s):
    return html.escape(s, quote=True)


def render(videos, upcoming, new_ids):
    now = datetime.now(JST)
    updated = now.strftime("%Y年%m月%d日 %H:%M")
    categories = []
    for v in videos:
        if v["category"] not in categories:
            categories.append(v["category"])

    cards = []
    for v in videos:
        badge = '<span class="badge-new">NEW</span>' if v["id"] in new_ids else ""
        cards.append(f'''
      <a class="card" href="{esc(v["url"])}" target="_blank" rel="noopener"
         data-category="{esc(v["category"])}" data-search="{esc(v["title"])}">
        <div class="thumb">
          <img src="https://i.ytimg.com/vi/{esc(v["id"])}/mqdefault.jpg" alt=""
               loading="lazy"
               onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{esc(v["id"])}/hqdefault.jpg'">
          <span class="play" aria-hidden="true">▶</span>
          {badge}
        </div>
        <div class="card-body">
          <p class="card-title">{esc(v["title"])}</p>
          <p class="card-meta"><span class="chip chip-{cat_slug(v["category"])}">{esc(v["category"])}</span>
            <span class="date">{esc(v["date"])}</span></p>
        </div>
      </a>''')

    upcoming_items = "".join(
        f'<li>{esc(u["title"])}</li>' for u in upcoming
    )

    filter_buttons = '<button class="filter on" data-filter="">すべて</button>' + "".join(
        f'<button class="filter" data-filter="{esc(c)}">{esc(c)}</button>' for c in categories
    )

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>どてっぱん マニュアル動画一覧</title>
<style>
  :root {{
    --bg: #faf8f4;
    --surface: #ffffff;
    --ink: #29231d;
    --ink-soft: #6d6257;
    --line: #e6dfd5;
    --accent: #9c3f1e;
    --accent-ink: #ffffff;
    --header-bg: #241f1b;
    --header-ink: #f5efe7;
    --new: #c8401f;
    --shadow: 0 1px 3px rgba(41, 35, 29, .08), 0 4px 14px rgba(41, 35, 29, .06);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1c1916;
      --surface: #26221e;
      --ink: #ede7de;
      --ink-soft: #a89c8e;
      --line: #3a342d;
      --accent: #d97a50;
      --accent-ink: #1c1916;
      --header-bg: #141210;
      --header-ink: #f5efe7;
      --shadow: 0 1px 3px rgba(0, 0, 0, .4);
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    background: var(--bg); color: var(--ink);
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic Medium",
      "Noto Sans JP", sans-serif;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}
  header {{
    background: var(--header-bg); color: var(--header-ink);
    padding: 28px 20px 24px;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; }}
  .brand {{
    font-size: 12px; letter-spacing: .35em; color: var(--accent);
    filter: brightness(1.6); font-weight: 600;
  }}
  h1 {{ font-size: 22px; font-weight: 700; margin-top: 6px; letter-spacing: .04em; }}
  .header-sub {{ font-size: 13px; color: #b8ac9d; margin-top: 4px; }}
  .notice {{
    max-width: 1080px; margin: 20px auto 0; padding: 14px 16px;
    background: var(--surface); border: 1px solid var(--line);
    border-left: 4px solid var(--accent); border-radius: 6px;
    font-size: 13px; color: var(--ink-soft);
  }}
  .notice strong {{ color: var(--ink); }}
  main {{ max-width: 1080px; margin: 0 auto; padding: 20px 20px 48px; }}
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 8px 0 20px; }}
  #search {{
    flex: 1 1 220px; padding: 10px 14px; font-size: 15px;
    border: 1px solid var(--line); border-radius: 8px;
    background: var(--surface); color: var(--ink);
  }}
  #search:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; border-color: transparent; }}
  .filters {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .filter {{
    padding: 7px 14px; font-size: 13px; border-radius: 999px; cursor: pointer;
    border: 1px solid var(--line); background: var(--surface); color: var(--ink-soft);
    font-family: inherit;
  }}
  .filter.on {{ background: var(--accent); color: var(--accent-ink); border-color: var(--accent); font-weight: 600; }}
  .filter:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .count {{ font-size: 13px; color: var(--ink-soft); margin-bottom: 12px; }}
  .grid {{
    display: grid; gap: 16px;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  }}
  .card {{
    display: block; text-decoration: none; color: inherit;
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 10px; overflow: hidden; box-shadow: var(--shadow);
    transition: transform .12s ease;
  }}
  .card:hover {{ transform: translateY(-2px); }}
  .card:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .thumb {{ position: relative; aspect-ratio: 16 / 9; background: #000; }}
  .thumb img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .play {{
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 26px; text-shadow: 0 1px 6px rgba(0, 0, 0, .6); opacity: .85;
  }}
  .badge-new {{
    position: absolute; top: 8px; left: 8px; background: var(--new); color: #fff;
    font-size: 11px; font-weight: 700; letter-spacing: .08em;
    padding: 2px 8px; border-radius: 4px;
  }}
  .card-body {{ padding: 12px 14px 14px; }}
  .card-title {{ font-size: 14.5px; font-weight: 600; line-height: 1.45; }}
  .card-meta {{ display: flex; align-items: center; gap: 8px; margin-top: 8px; }}
  .chip {{
    font-size: 11px; padding: 2px 9px; border-radius: 999px;
    border: 1px solid var(--line); color: var(--ink-soft);
  }}
  .date {{ font-size: 12px; color: var(--ink-soft); font-variant-numeric: tabular-nums; }}
  .empty {{ color: var(--ink-soft); font-size: 14px; padding: 24px 0; display: none; }}
  section.upcoming {{ margin-top: 40px; }}
  section.upcoming h2 {{
    font-size: 15px; font-weight: 700; letter-spacing: .06em;
    padding-bottom: 8px; border-bottom: 2px solid var(--line); margin-bottom: 12px;
  }}
  section.upcoming ul {{ list-style: none; display: flex; flex-wrap: wrap; gap: 8px; padding: 0; }}
  section.upcoming li {{
    font-size: 13px; color: var(--ink-soft); background: var(--surface);
    border: 1px dashed var(--line); border-radius: 6px; padding: 6px 12px;
  }}
  footer {{
    border-top: 1px solid var(--line); padding: 18px 20px 28px;
    font-size: 12px; color: var(--ink-soft); text-align: center;
  }}
  @media (prefers-reduced-motion: reduce) {{
    .card {{ transition: none; }}
  }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <p class="brand">DOTEPPAN</p>
    <h1>どてっぱん マニュアル動画一覧</h1>
    <p class="header-sub">調理・接客・清掃の手順は、この動画マニュアルで確認できます。</p>
  </div>
</header>

<div class="notice">
  <strong>ご利用にあたって:</strong>
  このページは現在作成中のため、内容が不完全な部分があります。今後も随時更新していきますので、定期的にご確認ください。
  従業員の皆さまへこのページのURLをお渡しいただくのは問題ありませんが、<strong>部外者への共有はお控えください</strong>。
</div>

<main>
  <div class="toolbar">
    <input id="search" type="search" placeholder="動画を検索(例: 焼き方、清掃)" aria-label="動画を検索">
    <div class="filters" role="group" aria-label="カテゴリで絞り込み">
      {filter_buttons}
    </div>
  </div>
  <p class="count"><span id="shown">{len(videos)}</span> / {len(videos)} 本を表示中</p>

  <div class="grid" id="grid">
{"".join(cards)}
  </div>
  <p class="empty" id="empty">該当する動画が見つかりませんでした。</p>

  <section class="upcoming">
    <h2>準備中の動画({len(upcoming)}本)</h2>
    <ul>
      {upcoming_items}
    </ul>
  </section>
</main>

<footer>
  最終更新: {updated}(毎日自動チェック・更新)<br>
  このページはスプレッドシート「マニュアル動画リスト」から自動生成されています。
</footer>

<script>
  var search = document.getElementById("search");
  var buttons = document.querySelectorAll(".filter");
  var cards = document.querySelectorAll(".card");
  var shown = document.getElementById("shown");
  var empty = document.getElementById("empty");
  var activeFilter = "";

  function apply() {{
    var q = search.value.trim().toLowerCase();
    var n = 0;
    cards.forEach(function (c) {{
      var okCat = !activeFilter || c.dataset.category === activeFilter;
      var okText = !q || c.dataset.search.toLowerCase().indexOf(q) !== -1;
      var show = okCat && okText;
      c.style.display = show ? "" : "none";
      if (show) n++;
    }});
    shown.textContent = n;
    empty.style.display = n === 0 ? "block" : "none";
  }}
  search.addEventListener("input", apply);
  buttons.forEach(function (b) {{
    b.addEventListener("click", function () {{
      buttons.forEach(function (x) {{ x.classList.remove("on"); }});
      b.classList.add("on");
      activeFilter = b.dataset.filter;
      apply();
    }});
  }});
</script>
</body>
</html>
'''


def cat_slug(name):
    return {"調理": "cook", "接客": "service", "清掃・準備": "clean"}.get(name, "other")


def main():
    print("スプレッドシートを取得しています...")
    rows = fetch_rows()
    videos, upcoming = parse(rows)
    print(f"公開済み動画: {len(videos)}本 / 準備中: {len(upcoming)}本")

    # 前回のスナップショットと比較して新着を検出(初登場から14日間はNEWバッジを表示)
    today = datetime.now(JST).strftime("%Y-%m-%d")
    try:
        with open("videos.json", encoding="utf-8") as f:
            prev = {v["id"]: v.get("first_seen", today)
                    for v in json.load(f)["videos"]}
        first_run = False
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        prev = {}
        first_run = True

    new_ids = set()
    added_now = []
    for v in videos:
        v["first_seen"] = prev.get(v["id"], today)
        if not first_run and v["id"] not in prev:
            added_now.append(v["title"])
        days = (datetime.now(JST) -
                datetime.strptime(v["first_seen"], "%Y-%m-%d").replace(tzinfo=JST)).days
        if not first_run and days <= 14:
            new_ids.add(v["id"])

    if first_run:
        print("初回実行のため、新着判定はスキップします。")
    elif added_now:
        print("新着動画: " + "、".join(added_now))
    else:
        print("新着動画はありません。")

    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump({"videos": videos, "upcoming": upcoming},
                  f, ensure_ascii=False, indent=1)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render(videos, upcoming, new_ids))
    print("index.html を生成しました。")


if __name__ == "__main__":
    sys.exit(main())
