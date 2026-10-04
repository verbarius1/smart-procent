#!/usr/bin/env python3
"""Выпуск новой версии лендинга.

    python3 tools/release.py "Что изменилось"

Что делает:
  1. Берёт следующий номер версии из versions.json.
  2. Проставляет этот номер в index.html (плашка «Версия N» и проверка свежести).
  3. Сохраняет копию страницы в v/N/index.html — она больше не меняется.
  4. Дописывает версию в versions.json и пересобирает список версий v/index.html.

После этого закоммитьте и запушьте изменения. Главная ссылка покажет новую версию,
а прежние останутся по адресам v/1/, v/2/ и т. д.
"""
import datetime
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS = os.path.join(ROOT, 'versions.json')
INDEX = os.path.join(ROOT, 'index.html')
TZ = datetime.timezone(datetime.timedelta(hours=3))  # Москва
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
          'августа', 'сентября', 'октября', 'ноября', 'декабря']


def human_date(iso):
    d = datetime.datetime.fromisoformat(iso)
    return f'{d.day} {MONTHS[d.month - 1]} {d.year}, {d:%H:%M}'


def load_versions():
    if not os.path.exists(VERSIONS):
        return {'latest': 0, 'versions': []}
    with open(VERSIONS, encoding='utf-8') as f:
        return json.load(f)


def save_versions(data):
    with open(VERSIONS, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def stamp_live(page, n):
    """Проставить номер версии в живую страницу."""
    page, a = re.subn(r'var PAGE_VERSION = \d+;', f'var PAGE_VERSION = {n};', page)
    page, b = re.subn(r'<span id="pageVersion">\d+</span>', f'<span id="pageVersion">{n}</span>', page)
    if not (a and b):
        raise SystemExit('В index.html не найдены метки версии (PAGE_VERSION / pageVersion)')
    return page


def archive_page(page, n, date_iso):
    """Сделать из страницы замороженную копию для v/N/."""
    # проверка свежести нужна только живой странице
    page = re.sub(r'<!--live-only-->.*?<!--/live-only-->\n?', '', page, flags=re.S)
    # пути: копия лежит на два уровня глубже
    page = page.replace('fetch(\'series.json\'', 'fetch(\'../../series.json\'')
    page = re.sub(r'(["\'(])assets/', r'\1../../assets/', page)
    bar = ('<div class="proto" role="note" style="background:#1C1C1F;color:#fff;font-size:13px;'
           'line-height:1.4;text-align:center;padding:8px 16px">'
           f'Архив: версия {n} от {html.escape(human_date(date_iso))} · '
           '<a href="../../" style="color:#FFDD2D">Открыть актуальную</a> · '
           '<a href="../" style="color:#FFDD2D">Все версии</a></div>')
    page, k = re.subn(r'<div class="proto"[^>]*>.*?</div>', bar, page, count=1, flags=re.S)
    if not k:
        page = page.replace('<body>', '<body>\n' + bar, 1)
    return page


def write(path, text):
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def build_list(data):
    latest = data['latest']
    items = []
    for v in sorted(data['versions'], key=lambda x: -x['n']):
        n = v['n']
        badge = '<span class="badge">Актуальная</span>' if n == latest else ''
        href = '../' if n == latest else f'{n}/'
        items.append(
            f'<li><a class="item" href="{href}"><span class="num">{n}</span><span class="body">'
            f'<span class="meta">{html.escape(human_date(v["date"]))}{badge}</span>'
            f'<span class="title">{html.escape(v["title"])}</span></span>{ARROW}</a></li>')
    return LIST_TEMPLATE.replace('{{ITEMS}}', '\n'.join(items)).replace('{{LATEST}}', str(latest))


ARROW = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>')

LIST_TEMPLATE = '''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Версии лендинга «Смарт-процент»</title>
<style>
@font-face{font-family:'Inter';src:url('../assets/fonts/Inter.woff2') format('woff2');font-weight:400 700;font-display:swap}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter','Helvetica Neue',Arial,sans-serif;background:#fff;color:#333;font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:#1F66E5}
.wrap{max-width:760px;margin:0 auto;padding:40px 16px 64px}
h1{font-size:32px;line-height:1.15;font-weight:700;letter-spacing:-.02em}
@media(min-width:768px){h1{font-size:44px}.wrap{padding-top:64px}}
.lead{color:#5F636B;margin-top:12px}
.how{background:#F6F7F8;border-radius:20px;padding:16px 20px;margin-top:24px;font-size:15px}
.how p+p{margin-top:6px}
.how code{font-family:inherit;font-weight:600;color:#333;white-space:nowrap}
.list{list-style:none;margin-top:24px;display:grid;gap:8px}
.item{display:flex;align-items:center;gap:14px;background:#F6F7F8;border-radius:20px;padding:16px;color:#333;text-decoration:none;transition:background-color .15s ease}
.item:hover{background:#EDEEF0}
.num{flex:0 0 44px;height:44px;border-radius:12px;background:#fff;display:grid;place-items:center;font-weight:700;font-size:18px}
.body{flex:1;min-width:0}
.meta{font-size:14px;color:#5F636B;display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}
.badge{background:#FFDD2D;color:#333;border-radius:8px;padding:1px 8px;font-size:13px;font-weight:600}
.title{display:block;margin-top:2px;font-size:15px;line-height:1.4}
.item svg{flex:0 0 20px;color:#5F636B}
</style>
</head>
<body>
<div class="wrap">
  <h1>Версии лендинга «Смарт-процент»</h1>
  <p class="lead">Прототип для согласования, не официальная страница Т‑Банка. Сейчас актуальна версия {{LATEST}}.</p>
  <div class="how">
    <p>Актуальная версия всегда по ссылке <a href="../">verbarius1.github.io/smart-procent</a></p>
    <p>Любую версию можно открыть по номеру: <code>…/smart-procent/v/НОМЕР/</code> или <code>…/smart-procent/?v=НОМЕР</code></p>
  </div>
  <ol class="list">
{{ITEMS}}
  </ol>
</div>
</body>
</html>
'''


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise SystemExit(__doc__)
    title = sys.argv[1].strip()
    data = load_versions()
    n = data['latest'] + 1
    date_iso = datetime.datetime.now(TZ).replace(second=0, microsecond=0).isoformat()
    with open(INDEX, encoding='utf-8') as f:
        page = stamp_live(f.read(), n)
    write(INDEX, page)
    write(os.path.join(ROOT, 'v', str(n), 'index.html'), archive_page(page, n, date_iso))
    data['versions'].append({'n': n, 'date': date_iso, 'title': title})
    data['latest'] = n
    save_versions(data)
    write(os.path.join(ROOT, 'v', 'index.html'), build_list(data))
    print(f'Версия {n} готова: v/{n}/. Закоммитьте и запушьте изменения.')


if __name__ == '__main__':
    main()
