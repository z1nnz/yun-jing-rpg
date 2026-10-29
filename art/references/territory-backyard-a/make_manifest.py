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
    'TY05': '練功地面兩種排法：A 不規則大石板放射狀圍繞木樁，B 長方石板錯縫，木樁四周一圈小方石；中央磨亮、縫裡長草、一塊裂、一塊下陷；側面 0.1 m 厚。木樁用既有的 agility-post，不重做。',
    'TY06': '石鎖（0.35 m，提把磨亮，側面雲紋）、石擔（1.5 m 木桿、兩個 0.45 m 石輪、麻繩）、兵器架（1.2 × 1.5 m，A 字木架，棍、木劍、槍）。三件都做。',
    'TY07': '圍籬模組 1.1 m：竹片直段 2 m（A）、編竹直段 2 m（B）、直段 1 m、轉角、收尾、柴門開／關；柱與橫檔高度一致，下段疊幾塊石頭。圖中柴門開啟時多了門楣，建模不加。',
    'TY08': '晾藥架 1.9 × 0.7 × 1.7 m：兩組竹 A 字架、三根橫竿、麻繩綁結、下層兩個圓竹篩；附掛滿草藥的狀態。圖中背景的竹籬不屬於這件。',
    'TY09': '生活雜物 6 件：水缸（0.6 m、木蓋、瓢）、竹籃 0.35 m、鋤頭 1.4 m、木桶 0.45 m、柴堆 1.0 × 0.7 m 加頂板、矮凳 0.3 m；附 1.6 × 1.6 m 院角配置俯視。',
    'TY10': '碎石小徑 1.1 m 寬：直段 A（碎石＋兩塊踏石）、直段 B（只有碎石、中間踩出的淺痕）、收尾（圓頭＋平門檻石）；側面高出地面不超過 2 cm。圖上面板誤標為 FRONT／SIDE／BACK，實際是三個俯視模組；收尾圖中的木門屬於屋子（B 的工作），不做。',
}
VIEWS = {'TY02': ['SPROUT', 'YOUNG', 'GROWN', 'MATURE'], 'TY03': ['FLOATING', 'STANDING', 'BUD', 'BLOOM'], 'TY05': ['LAYOUT A', 'LAYOUT B', 'SIDE'],
         'TY10': ['STRAIGHT A', 'STRAIGHT B', 'END']}
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
