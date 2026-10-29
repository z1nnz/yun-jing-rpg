"""Write image-manifest.json: size, SHA-256 and the review note for every saved reference sheet (run after generating)."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = {
    'TY01': '靈田田床：2.4 × 3.2 m、田埂高約 0.35 m；夯土田埂外砌灰青石，四角舊木樁綁麻繩，長邊有劈竹引水口與石缺口。下方附濕土、積水（約 6 cm）兩態。'
            '圖中畫成 5 條壟，建模改成 3 條壟，配合每塊田 3 × 4 叢；引水口放在朝中間小徑的長邊。',
    'TY02': '青靈草四階段（嫩芽 0.08 m、幼株 0.22 m、成株 0.40 m、成熟 0.48 m）；成熟期只有葉尖微光。下方附成株的三種叢形（直立、側傾、開散）與田中配置俯視。'
            '俯視圖是 3 × 3，建模照工作包改成 3 × 4。',
    'TY03': '淨水蓮四階段（浮葉、立葉、花苞 0.5 m、開花），蓮葉 0.15–0.35 m 大小不一，花心微光。'
            '圖中的竹框只是展示用，不採用：淨水蓮種在 TY01 的積水狀態裡。',
    'TY04': '院角舊石燈（守燈）：0.6 m 寬、1.7 m 高，灰青石方座、八角柱、木格紙窗燈室、翹角小石蓋，有苔與缺角；附燈室五段亮度。'
            '圖中缺月記號在正、背面都畫得太明顯；建模時只刻在一面、刻得很淺很小。',
}
VIEWS = {'TY02': ['SPROUT', 'YOUNG', 'GROWN', 'MATURE'], 'TY03': ['FLOATING', 'STANDING', 'BUD', 'BLOOM']}
out = []
for p in sorted(HERE.glob('*_three_view.png')):
    key = p.name.replace('_three_view.png', '')
    out.append({
        'id': key, 'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        'views': VIEWS.get(key, ['FRONT', 'SIDE', 'BACK']),
        'generator': 'OpenAI image generation via Codex CLI (codex exec), 2026-10-30; prompts in prompts.json + generate_three_view.sh',
        'review': REVIEW[key], 'reviewed': 'before modelling; build_backyard.py refuses to build an asset whose sheet is missing',
    })
(HERE / 'image-manifest.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print(len(out), 'entries')
