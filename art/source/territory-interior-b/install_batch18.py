"""Install TerritoryInterior18 into the main delivery folders and register it in asset_catalog.json.

  python install_batch18.py            (plain CPython 3, no third-party packages)

Copies Models/<ID>/v001 and ArtLibrary/Turnarounds/<ID>_v001 from the batch into the project root,
refuses to overwrite an existing different file, verifies SHA-256 on both sides, writes installation.json.
"""
import json, hashlib, shutil, sys
from pathlib import Path

BATCH = Path(__file__).resolve().parents[1]
ROOT = BATCH.parents[2]
VER = 'v001'
CATEGORY = '新手領地／屋內家具'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def copy_tree(src, dst, log):
    for f in sorted(src.rglob('*')):
        if f.is_dir(): continue
        t = dst / f.relative_to(src); t.parent.mkdir(parents=True, exist_ok=True)
        if t.exists() and sha(t) != sha(f):
            sys.exit(f'REFUSING to overwrite different file: {t}')
        if not t.exists(): shutil.copy2(f, t)
        a, b = sha(f), sha(t)
        assert a == b, t
        log.append({'file': str(t.relative_to(ROOT)).replace('\\', '/'), 'sha256': a, 'batch_copy': str(f.relative_to(ROOT)).replace('\\', '/')})

def main():
    log = []; ids = sorted(p.name for p in (BATCH / 'Models').iterdir() if (p / VER / 'validation.json').exists())
    for aid in ids:
        copy_tree(BATCH / 'Models' / aid / VER, ROOT / 'Models' / aid / VER, log)
        copy_tree(BATCH / 'ArtLibrary/Turnarounds' / f'{aid}_{VER}', ROOT / 'ArtLibrary/Turnarounds' / f'{aid}_{VER}', log)
    cat_path = ROOT / 'ArtLibrary/asset_catalog.json'
    cat = json.loads(cat_path.read_text(encoding='utf-8'))
    have = {e['id'] for e in cat['entries']}; added = []
    for aid in ids:
        if aid in have: continue
        info = json.loads((BATCH / 'Models' / aid / VER / 'model_info.json').read_text(encoding='utf-8'))
        val = json.loads((BATCH / 'Models' / aid / VER / 'validation.json').read_text(encoding='utf-8'))
        views = sorted(p.name for p in (ROOT / 'ArtLibrary/Turnarounds' / f'{aid}_{VER}').glob('*.png'))
        cat['entries'].append({
            'id': aid, 'name': info['name_zh'], 'category': CATEGORY, 'source_version': VER, 'source_path': f'Models/{aid}/{VER}',
            'blend': f'../Models/{aid}/{VER}/{aid}_{VER}.blend', 'fbx': f'../Models/{aid}/{VER}/{aid}_{VER}.fbx',
            'preview': f'Turnarounds/{aid}_{VER}/05_front_right.png', 'views': [f'Turnarounds/{aid}_{VER}/{v}' for v in views],
            'status': '烘焙貼圖與 LOD0–2 完成；未在 Unity 實際匯入驗證', 'batch': 'TerritoryInterior18',
            'unreal_import_verified': False, 'unity_import_verified': False, 'uv_baked': True, 'collision_ready': False,
            'lod_ready': True, 'batch_checks_all_pass': val['all_pass']})
        added.append(aid)
    cat['model_asset_sets'] += len(added); cat['consistent_turnaround_images'] += 10 * len(added)
    if 'ExpansionBatches/TerritoryInterior18/index.html' not in cat['supplemental_batches']:
        cat['supplemental_batches'].append('ExpansionBatches/TerritoryInterior18/index.html')
    cat['territory_interior_note'] = ('TerritoryInterior18: TI01-TI07 furniture and four TI08 display props for the newcomer territory interior, '
                                      'built for the Unity project (Y-up FBX, URP texture set). Not imported into Unity or Unreal here.')
    cat['updated'] = '2026-10-30'
    cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding='utf-8')
    (BATCH / 'installation.json').write_text(json.dumps({'installed_assets': ids, 'catalog_added': added, 'files': log}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('INSTALLED', len(ids), 'assets,', len(log), 'files; catalog +', len(added))

if __name__ == '__main__':
    main()
