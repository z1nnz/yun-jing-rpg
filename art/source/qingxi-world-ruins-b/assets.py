"""Asset registry for qingxi-world-ruins-b (work pack docs/execution/2026-11-01/02-B-world-ruins-kit.md)."""
import wr_kit_walls as W
import wr_kit_fence as F
import wr_scene_hut as H
import wr_houses as HS
import wr_props as P
import wr_scene_well as WL
import wr_scene_cart as CT

ASSETS = {}
for v, zh in (('Straight', '直段 3 m'), ('Corner', '轉角'), ('Collapsed', '塌了一半的斷段'), ('EndCap', '收頭（加做）')):
    ASSETS[f'R01_DryStoneWall_{v}'] = dict(
        zh=f'乾砌石牆・{zh}', batch=1, kind='kit', limit=None, embed=W.WALL_EMBED, tex=2048,
        build=(lambda v: (lambda: W.r01_wall(v)))(v), interfaces=W.WALL_INTERFACES[v],
        reference='art/references/qingxi-world-ruins-b/R01_DryStoneWall-three-views-v001.png')

for v, zh in (('Straight', '直段 2 m'), ('Corner', '轉角'), ('Leaning', '歪倒的一段'), ('EndPost', '端柱（加做）')):
    ASSETS[f'R02_BambooFence_{v}'] = dict(
        zh=f'竹籬笆・{zh}', batch=1, kind='kit', limit=None, embed=F.FENCE_EMBED, tex=2048,
        build=(lambda v: (lambda: F.r02_fence(v)))(v), interfaces=F.FENCE_INTERFACES[v],
        reference='art/references/qingxi-world-ruins-b/R02_BambooFence-three-views-v001.png')

ASSETS['D3_AbandonedHut'] = dict(
    zh='廢棄小屋', batch=1, kind='scene', limit=H.LIMIT, embed=H.EMBED, tex=2048, build=H.d3_hut,
    slot={'world_position': [-116.5, 72.0], 'yaw_deg': 90, 'max_w_d_h_m': list(H.LIMIT),
          'front': '-Y in Blender (door side); face it towards the gold edge when placing'},
    reference='art/references/qingxi-world-ruins-b/D3_AbandonedHut-three-views-v002.png',
    closeups=[('close_door_interior', (.24, -.96, .115), 1.0, ((-1.4, 1.2, 1.0), 2.0)),
              ('close_tally', (-1, -.6, .05), 1.0, ((-.03, -1.87, 1.38), .6)),
              ('close_quiver', (.06, -1, .12), 1.0, ((-.66, 1.72, 1.42), .9)),
              ('close_bed', (.7, -.7, .55), 1.0, ((-1.83, .8, .55), 1.6)),
              ('close_scarf_repair', (.15, -1, .2), 1.0, ((1.2, -1.97, 2.37), .9)),
              ('close_daub_breach', (.3, -1, .15), 1.0, ((2.0, -1.9, 1.05), 1.0)),
              ('close_roof_damage', (.65, -.75, .6), 1.0, ((1.5, -.6, 2.8), 2.6))],
    extra_checks=H.hut_checks,
    notes=['Walk-in: door clear 1.04 m x 2.03 m (stone threshold 0.14 m above ground, earthen floor 0.12 m); '
           'the 2 x 2 m area x -1.3..0.7, y -1.6..0.4 is free of geometry and collision (checked on the export).',
           'Collision: floor slab, four wall hulls with the door gap, lintel, threshold step, bed, leaning door leaf. '
           'No roof collision (out of reach); fallen rafters and shards are visual only.',
           'Footing stones are embedded 5 cm below z = 0; place on level ground or sink slightly into a slope.',
           'Interior is lit only through the door and the fallen-in roof; the game scene may want a small fill light.'])


# hero 3/4 camera direction where the default (front right) would hide what the house is about
HERO_DIR = {'H05_LimewashAnnexHouse': (-.8, -1, .45)}

HOUSE_INFO = {
    'H01_StoneTimberHouse': ('厚重石木屋（炭青陶瓦）', 'H01_Charcoal_StoneTimber-v001.png',
                             [('close_roof_damage', (-.55, -.8, .5), 1.0, ((-1.9, -1.2, 2.5), 2.6)),
                              ('close_door_interior', (.2, -.97, .15), 1.0, ((0.0, .6, 1.0), 2.4)),
                              ('close_stone_wall', (.25, -1, .1), 1.0, ((1.3, -1.9, .9), 1.6))]),
    'H07_DarkFrameHouse': ('補板木構屋（煙紫灰陶瓦）', 'H07_SmokeViolet_DarkFrame-v001.png',
                           [('close_corner_collapse', (.6, -.75, .35), 1.0, ((2.0, -1.4, 1.4), 3.0)),
                            ('close_door_canopy', (.15, -1, .1), 1.0, ((-.8, -1.9, 1.6), 2.4)),
                            ('close_door_interior', (.15, -.97, .12), 1.0, ((-.2, .4, 1.0), 2.4))]),
    'H05_LimewashAnnexHouse': ('白灰牆側間屋（灰藍陶瓦）', 'H05_BlueGrey_Limewash-v001.png',
                               [('close_roof_damage', (.2, -.85, .5), 1.0, ((.45, -1.5, 2.6), 2.2)),
                                ('close_annex', (-.75, -.6, .2), 1.0, ((-2.5, -.6, 1.2), 2.6)),
                                ('close_door_interior', (-.2, -.97, .12), 1.0, ((.3, .4, 1.0), 2.4))]),
    'H04_StrawThatchHouse': ('茅草屋（金黃茅草）', 'H04_Straw_Thatch-v001.png',
                             [('close_gable_collapse', (-.85, -.5, .3), 1.0, ((-2.1, -.5, 2.0), 2.8)),
                              ('close_thatch_ridge', (.3, -.85, .45), 1.0, ((.8, 0, 3.1), 1.8)),
                              ('close_door_interior', (.1, -.97, .12), 1.0, ((-.1, .4, 1.0), 2.4))]),
    'H03_BambooWeaveHouse': ('竹編屋（苔綠劈竹）', 'H03_MossGreen_Bamboo-v001.png',
                             [('close_ridge_hole', (.15, -.8, .55), 1.0, ((0, -.4, 2.9), 2.2)),
                              ('close_torn_mat', (.9, -.35, .1), 1.0, ((2.3, .75, 1.0), 1.8)),
                              ('close_porch_door', (.2, -1, .12), 1.0, ((-.15, -1.8, 1.4), 2.6))]),
    'H06_RustShingleHouse': ('木板屋（鏽棕木瓦）', 'H06_RustBrown_Log-v001.png',
                             [('close_roof_hole', (.75, .55, .5), 1.0, ((1.1, 1.0, 2.7), 2.2)),
                              ('close_gable_door', (.1, -1, .1), 1.0, ((0, -1.85, 1.6), 3.0)),
                              ('close_back_patch', (.2, 1, .1), 1.0, ((0, 1.85, 1.6), 2.2))]),
    'H02_RammedEarthHouse': ('夯土屋（赭紅陶瓦）', 'H02_Russet_RammedEarth-v001.png',
                             [('close_corner_collapse', (.65, .65, .35), 1.0, ((1.8, 1.5, 1.6), 3.0)),
                              ('close_earth_wall', (-.2, -1, .1), 1.0, ((-1.2, -1.95, 1.2), 2.0)),
                              ('close_door_interior', (.1, -.97, .12), 1.0, ((-.1, .4, 1.0), 2.4))]),
    'H08_SandStonePlasterHouse': ('石灰抹面石屋（淺沙木瓦）', 'H08_Sand_StonePlaster-v001.png',
                                  [('close_roof_dip', (.1, .8, .55), 1.0, ((.1, 1.0, 2.9), 2.4)),
                                   ('close_stone_plaster', (-.3, -1, .1), 1.0, ((1.4, -1.9, 1.2), 2.0)),
                                   ('close_door_interior', (.1, -.97, .12), 1.0, ((-.1, .4, 1.0), 2.4))]),
}


def _house(aid):
    zh, ref, raw = HOUSE_INFO[aid]
    # texture budget: 4 atlases x 1024 at >= 125 px/m, WebP inside the GLB (PNG kept in Textures/ for Unity)
    spec = dict(zh=zh, batch=3, kind='scene', limit=HS.LIMIT, embed=HS.EMBED, tex=1024, min_texel=125, glb_image='WEBP',
                slot={'max_w_d_h_m': list(HS.LIMIT), 'front': '-Y in Blender (door side)',
                      'note': 'variant of the D3 slot; same footprint limit, any D3-sized plot'},
                reference=f'art/references/qingxi-world-ruins-b/house-variants/{ref}',
                closeups=[], extra_checks=HS.house_checks, rebalance=True, hero=HERO_DIR.get(aid, (.75, -1, .45)),
                notes=['Walk-in: door clear opening at least 0.9 x 1.9 m; a 2 x 2 m interior area is free of geometry and collision '
                       '(checked on the export, box recorded in validation).',
                       'Collision: floor slab, wall hulls following the standing wall height (door gap left open), lintel, threshold, '
                       'bed, leaning door leaf, rubble mounds, lean-to posts. No roof collision.',
                       'Footing stones are embedded 5 cm below z = 0.'])

    def build():
        HS.build_house(HS.HOUSES[aid])
        o = HS.K.offset
        spec['closeups'][:] = [(n, d, m, ((t[0] + o.x, t[1] + o.y, t[2]), e)) for n, d, m, (t, e) in raw]
    spec['build'] = build
    return spec


for _aid in HOUSE_INFO: ASSETS[_aid] = _house(_aid)


# ---------------------------------------------------------------- batch 2
ASSETS['R05_Milestone'] = dict(
    zh='里程石', batch=2, kind='prop', limit=None, embed=P.MS_EMBED, tex=1024, build=P.r05_milestone,
    reference='art/references/qingxi-world-ruins-b/R05_Milestone-three-views-v001.png',
    closeups=[('close_panel', (.25, -1, .12), 1.0, ((0, -.17, .72), .95)),
              ('close_crown', (-.6, -.7, .5), 1.0, ((0, 0, 1.15), .8))],
    notes=['Blank inscription panel 0.34 x 0.65 m on the -Y face, bottom edge 0.33 m above ground; no carved text '
           '(place names are added in game).',
           'Set 0.25 m into the ground; the base is roughly squared so it also stands on a slight slope.',
           'Collision: one convex hull of the stone.'])
ASSETS['R04_StoneLanternIntact'] = dict(
    zh='石燈籠（完整）', batch=2, kind='prop', limit=None, embed=P.LT_EMBED, tex=1024, build=P.r04_lantern_intact,
    reference='art/references/qingxi-world-ruins-b/R04_StoneLanternIntact-three-views-v001.png',
    closeups=[('close_chamber', (.7, -1, .25), 1.0, ((0, 0, 1.18), .62)),
              ('close_seam', (.4, -1, .1), 1.0, ((0, 0, .5), .5))],
    notes=['1.65 m tall, 0.68 m at the eaves; the foot is set 0.05 m into the ground.',
           'Lamp chamber is open on four sides and sooted inside; no flame or light source in the model.',
           'Old repair seam on the shaft at 0.50 m (upper drum reset slightly off true on a lime bed).',
           'Collision: three convex hulls (foot, shaft, head).'])
ASSETS['R04_StoneLanternBroken'] = dict(
    zh='石燈籠（殘損）', batch=2, kind='prop', limit=None, embed=P.LT_EMBED, tex=1024, build=P.r04_lantern_broken,
    reference='art/references/qingxi-world-ruins-b/R04_StoneLanternBroken-three-views-v001.png',
    closeups=[('close_rim', (.5, -.8, .9), 1.0, ((0, 0, 1.1), .62)),
              ('close_foot', (.7, -1, .3), 1.0, ((0, 0, .2), .7))],
    notes=['1.25 m surviving height, 0.58 m footprint; the cap and finial are gone and not modelled nearby.',
           'Post heads and two lintels are fractured at uneven heights; fresh breaks use a lighter warm-grey stone.',
           'Lamp basin (chamber floor) and chamber insides are sooted.',
           'Collision: three convex hulls (foot, shaft, head).'])
ASSETS['R03_FirewoodNeat'] = dict(
    zh='柴堆（整齊）', batch=2, kind='prop', limit=None, embed=0.0, tex=2048, build=P.r03_firewood_neat,
    reference='art/references/qingxi-world-ruins-b/R03_FirewoodNeat-three-views-v002.png',
    closeups=[('close_ends', (.3, -1, .2), 1.0, ((-.2, -.35, .45), .7)),
              ('close_bundle', (.6, -1, .6), 1.0, ((.3, 0, .8), .6))],
    notes=['About 1.7 x 0.74 x 0.9 m. Split billets run front to back, so front and back both show cut ends.',
           'Two timber sleepers carry the stack; small round billets are cribbed at both ends behind stakes.',
           'Top: one long half log and a bundle of three round logs tied with two hemp wraps.',
           'Collision: one box around the stack.'])
ASSETS['R03_FirewoodScattered'] = dict(
    zh='柴堆（散亂）', batch=2, kind='prop', limit=None, embed=0.0, tex=2048, build=P.r03_firewood_scattered,
    reference='art/references/qingxi-world-ruins-b/R03_FirewoodScattered-three-views-v001.png',
    closeups=[('close_heap', (.4, -1, .35), 1.0, ((0, 0, .3), .8)),
              ('close_loose', (-.6, -1, .5), 1.0, ((-.7, .1, .1), .55))],
    notes=['Low asymmetric heap within about 1.85 x 1.1 x 0.62 m, plus three loose pieces alongside.',
           'Placement is settled procedurally: every billet rests on the ground or on billets placed before it.',
           'Collision: three convex hulls (west, middle, east thirds of the heap).'])
ASSETS['D3_DryWell'] = dict(
    zh='枯井', batch=2, kind='scene', limit=WL.LIMIT, embed=WL.EMBED, tex=2048, build=WL.d3_well,
    reference='art/references/qingxi-world-ruins-b/D3_DryWell-three-views-v001.png',
    closeups=[('close_shaft', (.15, -.35, 1.0), 1.0, ((0, 0, .1), 1.3)),
              ('close_rope_end', (.4, -1, .1), 1.0, ((.07, -.1, 1.25), .45)),
              ('close_repair', (-1, -.6, .1), 1.0, ((-.86, 0, 1.0), .8)),
              ('close_broken_lip', (.5, -1, .5), 1.0, ((.29, -.53, .62), .6))],
    notes=['Ring 1.42 m outer / 0.88 m inner diameter, 0.68 m high; envelope within 1.8 x 1.8 x 2.2 m above ground.',
           'The stone-lined shaft continues to 1.6 m below ground with a dry silt floor: the terrain must be cut '
           '(an 0.88 m round hole) where the well is placed, or the shaft is hidden by the ground.',
           'One coping stone has lost its outer top corner; the rope is snapped about 0.7 m below the drum, no bucket.',
           'Collision: twelve convex blocks round the open ring (the shaft stays open) and the two uprights.'])
ASSETS['A2_OverturnedCart'] = dict(
    zh='翻覆推車', batch=2, kind='scene', limit=CT.LIMIT, embed=CT.EMBED, tex=2048, build=CT.a2_cart,
    reference='art/references/qingxi-world-ruins-b/A2_OverturnedCart-three-views-v002.png',
    closeups=[('close_spill', (.4, -1, .7), 1.0, ((-.65, -.5, .12), 1.0)),
              ('close_loose_wheel', (-1, -.5, .35), 1.0, ((-1.5, .05, .45), 1.3)),
              ('close_axle', (.5, -1, .6), 1.0, ((0, 0, .8), 1.0))],
    notes=['The AI reference (v002) scored 81 and is not consistent between views; it is NOT an approved modelling basis. '
           'The model keeps its parts list but its pose is computed: the cart is built upright and tipped as one rigid '
           'body onto the first stable edge of its convex hull when rolled towards -Y.',
           'One wheel stays on the axle; the other has come off and stands on its rim behind the tail, its hub resting '
           'against the end planks. Two burlap sacks lie by the open bed; one is torn and spills grain.',
           'Collision: convex hulls for the cart body, each shaft, both wheels and the sacks.'])
