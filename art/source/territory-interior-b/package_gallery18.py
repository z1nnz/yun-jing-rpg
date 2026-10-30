"""Write index.html, inventory.json and validation.json for TerritoryInterior18 from the files on disk.

  python package_gallery18.py      (plain CPython 3)
Only reports checks that were actually run (read from each asset's validation.json / layout_check.json).
"""
import json, hashlib, html
from pathlib import Path

BATCH = Path(__file__).resolve().parents[1]; VER = 'v001'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ids = sorted(p.name for p in (BATCH / 'Models').iterdir() if (p / VER / 'validation.json').exists())
    cards, inv, vals = [], [], []
    for aid in ids:
        d = BATCH / 'Models' / aid / VER; info = json.loads((d / 'model_info.json').read_text(encoding='utf-8'))
        val = json.loads((d / 'validation.json').read_text(encoding='utf-8')); vals.append(val)
        views = sorted((BATCH / 'ArtLibrary/Turnarounds' / f'{aid}_{VER}').glob('*.png'))
        extra = [p for p in sorted(d.glob('*.png')) if not p.name.endswith('_hero.png')]
        tris = {k: sum(v.values()) for k, v in info['lods'].items()}
        rows = ''.join(f'<li class="{"ok" if c["pass"] else "bad"}">{"通過" if c["pass"] else "未通過"}：{html.escape(c["check"])}</li>' for c in val['checks'])
        layers = info['naming_three_layers']
        rel = lambda p: p.relative_to(BATCH).as_posix()
        cards.append(f'''
<section class="asset" id="{aid}">
  <h2>{aid}　{html.escape(info["name_zh"])}</h2>
  <p class="meta">格位 {html.escape(info["interior_slot"])}｜尺寸 {" × ".join(f"{v:.3f}" for v in info["dimensions_m"])} m（上限 {" × ".join(map(str, info["slot_limit_m"]))}）｜三角面 LOD0 {tris["LOD0"]:,}／LOD1 {tris["LOD1"]:,}／LOD2 {tris["LOD2"]:,}｜貼圖 {info["texture_size_px"]} px</p>
  <p class="meta">表面：{html.escape(layers["surface"])}｜典故：{html.escape(layers["allusion"])}｜伏筆（內部）：{html.escape(layers["foreshadowing_internal_only"])}</p>
  <img class="hero" src="{rel(d / f"{aid}_hero.png")}" alt="{aid} 主視圖">
  <div class="views">{"".join(f'<figure><img src="{rel(v)}" loading="lazy"><figcaption>{v.stem}</figcaption></figure>' for v in views)}</div>
  <div class="extra">{"".join(f'<figure><img src="{rel(v)}" loading="lazy"><figcaption>{v.stem}</figcaption></figure>' for v in extra)}</div>
  <ul class="checks">{rows}</ul>
</section>''')
        files = [p for p in d.rglob('*') if p.is_file()] + views
        inv.append({'asset': aid, 'files': [{'file': rel(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(files)]})
    pres = BATCH / 'Presentation'; pimgs = sorted(pres.glob('*.png')) if pres.exists() else []
    layout = json.loads((pres / 'layout_check.json').read_text(encoding='utf-8')) if (pres / 'layout_check.json').exists() else None
    lay_html = ''
    if layout:
        lay_html = '<ul class="checks">' + ''.join(
            f'<li class="{"ok" if v["pass"] else "bad"}">{"通過" if v["pass"] else "未通過"}：{k} 門前 1.2 m 淨空 {("（擋住：" + "、".join(v["blocking"]) + "）") if v["blocking"] else ""}</li>'
            for k, v in layout['door_clearance'].items()) + ''.join(
            f'<li class="{"ok" if v["pass"] else "bad"}">{"通過" if v["pass"] else "未通過"}：{k} 前方 0.6 m 站立區 {("（擋住：" + "、".join(v["blocking"]) + "）") if v["blocking"] else ""}{"" if v["inside_room"] else "（站立區超出房間）"}</li>'
            for k, v in layout['approach'].items()) + ''.join(
            f'<li class="bad">重疊：{a} 與 {b}</li>' for a, b in layout['conflicts']) + '</ul>'
    page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>新手領地屋內 TI01–TI08</title>
<style>
:root{{--bg:#1d2022;--fg:#e9e4da;--muted:#a7a196;--ok:#8fc79a;--bad:#e59a8c;--card:#262a2c}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,"Noto Sans TC",sans-serif}}
main{{max-width:1280px;margin:0 auto;padding:24px 16px}}
h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:20px;margin:0 0 6px}} .meta{{color:var(--muted);margin:2px 0}}
.asset,.pres{{background:var(--card);border-radius:10px;padding:16px;margin:18px 0}}
.hero{{width:min(520px,100%);border-radius:6px;display:block;margin:10px 0}}
.views,.extra,.pgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}}
.extra{{grid-template-columns:repeat(auto-fill,minmax(260px,1fr));margin-top:8px}} .pgrid{{grid-template-columns:repeat(auto-fill,minmax(360px,1fr))}}
figure{{margin:0}} figure img{{width:100%;border-radius:4px;display:block}} figcaption{{font-size:12px;color:var(--muted)}}
.checks{{list-style:none;padding:0;margin:10px 0 0;font-size:13px}} .ok{{color:var(--ok)}} .bad{{color:var(--bad)}}
nav a{{color:var(--fg);margin-right:10px;font-size:13px}}
</style></head><body><main>
<h1>雲境｜新手領地屋內 TI01–TI08 v001</h1>
<p class="meta">程序化建模，程序材質烘焙成貼圖集；每件 LOD0–LOD2、十視圖、FBX（Y-up）。十視圖渲染的是匯出的 LOD0 加烘焙貼圖。未在 Unity 實際匯入驗證。</p>
<nav>{"".join(f'<a href="#{a}">{a}</a>' for a in ids)}<a href="#presentation">屋內展示</a></nav>
{"".join(cards)}
<section class="pres" id="presentation"><h2>屋內展示與配置檢查</h2>
<p class="meta">牆、地板、門洞為灰盒佔位（C2 室內套件未取得），不屬於本次交付。床、儲物箱、蒲團由原始建模腳本重建。</p>
<div class="pgrid">{"".join(f'<figure><img src="{p.relative_to(BATCH).as_posix()}" loading="lazy"><figcaption>{p.stem}</figcaption></figure>' for p in pimgs)}</div>
{lay_html}</section>
</main></body></html>'''
    (BATCH / 'index.html').write_text(page, encoding='utf-8')
    (BATCH / 'inventory.json').write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding='utf-8')
    summary = {'batch': 'TerritoryInterior18', 'date': '2026-10-30', 'assets': {v['asset']: {'all_pass': v['all_pass'], 'failed': [c['check'] for c in v['checks'] if not c['pass']]} for v in vals},
               'layout_check_pass': layout['pass'] if layout else None,
               'not_verified': ['Unity import and LODGroup creation', 'in-engine lighting/emission values', 'collision', 'C2 interior kit side-by-side', 'performance']}
    (BATCH / 'validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('GALLERY', len(ids), 'assets')

if __name__ == '__main__':
    main()
