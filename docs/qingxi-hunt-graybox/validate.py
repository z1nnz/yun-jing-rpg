"""Static geometry checks; not a substitute for Unity/NavMesh or playtesting.

Run: python docs/qingxi-hunt-graybox/validate.py [--render]
Only optional rendering requires Pillow; validation uses the standard library.
"""
import json
import math
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / 'apps/game/Assets/YunJing/Editor/QingxiHuntGraybox.json'


def xy(point):
    return point['x'], point['z']


def length(points):
    return sum(math.dist(xy(a), xy(b)) for a, b in zip(points, points[1:]))


def validate(data):
    markers = {m['name']: m['position'] for m in data['markers']}
    required = {'PlayerSpawn_01', 'PlayerSpawn_02', 'Merchant_Material', 'SafeReturn_01'}
    required |= {f'{prefix}_{i:02}' for prefix in ('TrailClue', 'HerbNode') for i in range(1, 7)}
    required |= {f'RabbitSpawn_{g}{i:02}' for g in 'ABC' for i in range(1, 3)}
    required |= {f'RabbitFlee_{g}{i:02}' for g in 'ABC' for i in range(1, 4)}
    assert set(markers) == required and len(markers) == len(data['markers']), 'Missing or duplicate markers'
    assert len(data['zones']) == 6
    assert data['bounds']['x'] == 220 and data['bounds']['z'] == 160
    assert all(m['y'] == 0 for m in markers.values()), 'Draft uses a flat walkable floor'

    def clear(x, z, radius):
        if abs(x) + radius >= 110 or abs(z) + radius >= 80:
            return False
        return not any(abs(x - b['position']['x']) <= b['size']['x'] / 2 + radius
                       and abs(z - b['position']['z']) <= b['size']['z'] / 2 + radius
                       for b in data['blockers'])

    for name, point in markers.items():
        assert clear(*xy(point), data['playerRadius']), f'Blocked marker: {name}'
    spawns = [p for n, p in markers.items() if 'Spawn_' in n]
    assert all(math.dist(xy(a), xy(b)) >= 8 for i, a in enumerate(spawns) for b in spawns[i+1:])

    # Sample the full corridor footprint, not just its centre line.
    for route in data['routes']:
        assert route['width'] >= 2.5
        for a, b in zip(route['points'], route['points'][1:]):
            distance = math.dist(xy(a), xy(b))
            assert distance > 0
            for i in range(math.ceil(distance * 4) + 1):
                t = min(1, i / math.ceil(distance * 4))
                x, z = a['x'] + (b['x']-a['x'])*t, a['z'] + (b['z']-a['z'])*t
                assert clear(x, z, route['width']/2), f'Obstructed corridor: {route["name"]} at {x:.1f},{z:.1f}'
            assert abs(b['y'] - a['y']) <= math.tan(math.radians(35)) * distance

    # Conservative 1 m grid: clearance includes cell half-diagonal and actor radius.
    # A reachable grid is evidence about this JSON's boxes, not a baked Unity NavMesh.
    start = tuple(round(c) for c in xy(markers['PlayerSpawn_01']))
    seen, queue = {start}, deque([start])
    while queue:
        x, z = queue.popleft()
        for p in ((x+1,z),(x-1,z),(x,z+1),(x,z-1)):
            if p not in seen and clear(*p, data['playerRadius'] + math.sqrt(.5)):
                seen.add(p); queue.append(p)
    assert all(tuple(round(c) for c in xy(p)) in seen for p in markers.values()), 'Disconnected marker'

    main, back = data['routes'][:2]
    clue_index = next(i for i, p in enumerate(main['points']) if p == markers['TrailClue_01'])
    clue_seconds = length(main['points'][:clue_index+1]) / data['walkSpeed']
    rabbit_seconds = length(main['points']) / data['walkSpeed']
    return_seconds = length(back['points']) / data['walkSpeed']
    assert 20 <= clue_seconds <= 30
    assert 60 <= rabbit_seconds <= 90
    assert 50 <= return_seconds <= 70
    result = {'kind': 'static JSON geometry only', 'markers': len(markers), 'zones': 6,
              'reachableGridCells': len(seen), 'speedMetresPerSecond': data['walkSpeed'],
              'guidedRouteSeconds': {'firstClue': round(clue_seconds, 2), 'firstRabbit': round(rabbit_seconds, 2),
                                     'return': round(return_seconds, 2)},
              'unityCompiled': False, 'navMeshTested': False, 'twoPlayerTested': False,
              'cameraTested': False}
    print(json.dumps(result, indent=2))
    return result


def render(data):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1320, 1100), '#f2f1e9')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    title = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 26)
    def p(x, z): return (660 + x*5, 510-z*5)
    draw.text((45,20), 'QINGXI HUNT | 220 x 160 m | Layout draft', fill='#203333', font=title)
    draw.text((45,58), 'Plan view only - NOT a Unity screenshot. Flat walkable surface: Y=0 m.', fill='#753c23', font=font)
    for x in range(-110,111,10): draw.line([p(x,-80),p(x,80)], fill='#d2d8d0')
    for z in range(-80,81,10): draw.line([p(-110,z),p(110,z)], fill='#d2d8d0')
    for b in data['zones']+data['blockers']:
        x,z=xy(b['position']); w,d=b['size']['x'],b['size']['z']
        color = '#5c6869' if b in data['blockers'] else '#b5d3c0'
        if b['kind']=='water': color='#a4d6e4'
        draw.rectangle([p(x-w/2,z+d/2),p(x+w/2,z-d/2)],fill=color)
    for r in data['routes']:
        color='#b26935' if r['name']=='MainExploration' else '#376ca8'
        if r['name'].startswith('Rabbit'): color='#825ca0'
        draw.line([p(*xy(v)) for v in r['points']], fill=color, width=max(3,round(r['width']*2)))
    for m in data['markers']:
        x,y=p(*xy(m['position'])); n=m['name']
        color='#ac493c' if n.startswith('Rabbit') else '#1e6853'
        draw.ellipse((x-4,y-4,x+4,y+4),fill=color)
        label=n.replace('RabbitSpawn_','S').replace('RabbitFlee_','F').replace('TrailClue_','T').replace('HerbNode_','H').replace('PlayerSpawn_','P').replace('Merchant_Material','Merchant').replace('SafeReturn_01','Safe return')
        draw.text((x+5,y+2),label,fill='#172b2c',font=font)
    for b in data['zones']:
        x,z=xy(b['position'])
        draw.text(p(x-b['size']['x']/2,z+b['size']['z']/2),b['name'],fill='#172b2c',font=font)
    lines=['N = +Z (up); E = +X (right). Each grid square = 10 m.',
           'Brown: guided exploration, 5 m wide. Blue: return, 6 m wide. Purple: rabbit circuits, 2.5 m wide.',
           'P: player | T: trail clue | H: herb | S: rabbit spawn | F: rabbit flee point.',
           'Dark boxes: collision / sight screens. Cyan: shallow-water visual proxy; solid floor at Y=0.',
           'Timing is distance / 4 m/s along the suggested route, not a recorded playtest.',
           'Unity compile, NavMesh, 3.5-6 m cameras, two-player traversal and mobile performance: NOT TESTED.']
    for i,line in enumerate(lines): draw.text((45,935+i*24),line,fill='#203333',font=font)
    image.save(HERE/'layout.png')


if __name__ == '__main__':
    data = json.loads(DATA.read_text(encoding='utf-8'))
    validate(data)
    if '--render' in sys.argv:
        render(data)
