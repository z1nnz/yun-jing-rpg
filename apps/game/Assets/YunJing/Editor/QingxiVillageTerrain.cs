using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // Continuous ground for the novice village, generated from tools/qingxi-terrain/novice-village.json:
    // gentle relief from height points, flat pads under each collaborator zone, roads that follow the
    // relief with a level cross-section, road/plaza/forest paint and grass kept out of roads and pads.
    // Same approach as QingxiEntranceTerrain (PR #48); kept separate so the two pilots don't edit one file.
    public static class QingxiVillageTerrain
    {
        const string Generated = "Assets/YunJing/Generated";
        const int HeightResolution = 513, PaintResolution = 512;   // 0.2 m per sample on a 100 m block: no stair-stepped banks
        const float BaseY = -1f, HeightRange = 24f;   // D3 climbs to 15 m; 16-bit heights keep sub-millimetre steps
        const float RoadBlend = 2.5f, PadBlend = 3f;

        [Serializable] public class Area { public float minX, minZ, sizeX, sizeZ; }
        [Serializable] public class Node { public string id; public float x, z; }
        [Serializable] public class Edge { public string id, from, to, surface; public float width; }
        [Serializable] public class Pad { public string id, surface; public float x, z, halfX, halfZ, height; }
        [Serializable] public class HeightPoint { public float x, z, height; }
        [Serializable] public class Checkpoint { public string name, node; }
        // A slot in the village plan. footprint = width, depth, height (m) along the model's own X/Z before yaw;
        // status: placed / ready (model exists, placed by the builder) / needed (no model yet, shown as a box).
        [Serializable]
        public class Placement
        {
            public string id, role, model, author, collider, block, zone, owner, status, phase, note;
            public float x, z, yaw, scale;
            public float[] footprint;
            public bool Needed => status == "needed" || string.IsNullOrEmpty(model);
        }
        [Serializable] public class Herb { public string id, kind; public float x, z; }
        [Serializable] public class FortuneSpot { public string id, title, passage, reward, condition; public float x, z; }
        [Serializable] public class Crossing { public float x, z; public int stones; }
        [Serializable]
        public class Creek
        {
            public float width = 4, depth = .9f, bank = 3, waterLevel = .6f;
            public float[] points = new float[0];   // x, z pairs from upstream to downstream
            public Crossing crossing;
            public bool sourceEnd = true;   // false when the creek carries on into the next block (D1 into D3)
            public int Count => points.Length / 2;
            public Vector2 this[int i] => new Vector2(points[2 * i], points[2 * i + 1]);
        }
        [Serializable]
        public class Layout
        {
            public int version;
            public Area bounds;
            public float noise;
            public Node[] nodes;
            public Edge[] edges;
            public Pad[] pads;
            public HeightPoint[] heightPoints;
            public Checkpoint[] checkpoints;
            public string[] route;
            public Placement[] placements;
            public Placement[] crossingSlots;   // slots off the pads (bridges over the creek)
            public Herb[] herbs;
            public FortuneSpot[] fortunes;   // 機緣 (K4): hidden finds, never on the map
            public Creek creek;
            public CreekKitSpan[] creekKit;   // D3: which river tiles (PR #45) line each stretch of the creek
            public Flat[] flats;              // ground levelled under built works that are not on a pad (the old channel)
            public float relief;              // metres of broad rolling relief on open ground (roads, pads, creek stay level)
            public float terrace;             // Liyue-style terrace step (m) on the relief; 0 for none
            public float cliffs;              // height (m) of the rock walls between shelves of land (the reference valleys); 0 for none
            public string block;              // block id; names the generated creek water mesh
            public bool isolated;             // a pocket world of its own (the territory): no blend to the shared world height
        }
        [Serializable] public class Flat { public string id, note; public float x, z, halfX, halfZ, height, blend = 1.5f; }
        [Serializable] public class CreekKitSpan { public float from, to; public string pieces, note; }

        // Distance to the creek's centre line, and the land height there (the bed follows the land, so the
        // water runs downhill). Returns +infinity when the layout has no creek.
        public static float CreekDistance(Layout layout, float x, float z, out float centreLand)
        {
            centreLand = 0;
            var c = layout.creek;
            if (c == null || c.Count < 2) return float.PositiveInfinity;
            float best = float.PositiveInfinity; var p = new Vector2(x, z);
            for (int i = 0; i + 1 < c.Count; i++)
            {
                Vector2 a = c[i], b = c[i + 1], ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f));
                var q = a + ab * t;
                float d = Vector2.Distance(p, q);
                if (d < best) { best = d; centreLand = LandAt(layout, q.x, q.y); }
            }
            return best;
        }

        /// <summary>Height of the water surface at a point on (or near) the creek centre line.</summary>
        public static float WaterHeight(Layout layout, float x, float z)
        {
            CreekDistance(layout, x, z, out float land);
            return land - layout.creek.depth + layout.creek.waterLevel;
        }

        // Seven grounds, after Liyue's valleys (docs/execution/liyue-terrain-standard.md): lush and sun-dried meadow in
        // patches, packed earth on the paths, stone slabs near the village, leaf-litter forest floor, creek gravel, and
        // the warm ochre rock that shows where the ground is too steep to hold grass.
        static readonly string[] LayerNames = { "VillageMeadow", "VillagePackedEarth", "VillagePlazaStone", "VillageForestFloor", "MeadowDry", "CreekGravel", "OchreRock" };
        static readonly Color[] Colors = {
            new Color(.32f, .5f, .22f), new Color(.55f, .43f, .29f), new Color(.55f, .53f, .48f), new Color(.42f, .4f, .26f),
            new Color(.58f, .62f, .30f), new Color(.52f, .50f, .45f), new Color(.6f, .52f, .42f)
        };
        static readonly string[] Kinds = { "grass", "earth", "slab", "litter", "grass", "gravel", "rock" };
        static readonly float[] Tiles = { 3, 4, 4, 4, 4, 2.5f, 7 };

        // A1 (the novice village) by default; other blocks pass their file under tools/qingxi-terrain/blocks/.
        public static Layout Load(string relative = "tools/qingxi-terrain/novice-village.json")
        {
            var file = Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", relative));
            if (!File.Exists(file)) throw new FileNotFoundException("Novice village layout missing", file);
            var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(file));
            if (layout == null || layout.version < 1 || layout.version > 2 || layout.bounds == null || layout.nodes == null || layout.edges == null || layout.pads == null)
                throw new InvalidDataException("Novice village layout is invalid");
            var ids = layout.nodes.Select(n => n.id).ToHashSet();
            foreach (var edge in layout.edges)
                if (edge.width <= 0 || !ids.Contains(edge.from) || !ids.Contains(edge.to))
                    throw new InvalidDataException("Invalid village road: " + edge.id);
            return layout;
        }

        static float Smooth(float a, float b, float value)
        {
            float t = Mathf.Clamp01((value - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        // Inverse-distance blend of the pad heights and the extra height points: smooth, no ridges.
        /// <summary>The planned land height eased to the shared world height near the block edge, as the terrain is:
        /// the creek and its river tiles follow this, so a creek crossing into the next block meets it at the same level.</summary>
        internal static float LandAt(Layout layout, float x, float z)
        {
            var area = layout.bounds;
            float border = Mathf.Min(Mathf.Min(x - area.minX, area.minX + area.sizeX - x), Mathf.Min(z - area.minZ, area.minZ + area.sizeZ - z));
            return layout.isolated ? BaseHeight(layout, x, z) : Mathf.Lerp(WorldBase(x, z), BaseHeight(layout, x, z), Smooth(1f, 12f, border));
        }

        internal static float BaseHeight(Layout layout, float x, float z)
        {
            if (layout.isolated) return Bowl(layout, x, z);
            float sum = 0, weights = 0;
            void Add(float px, float pz, float h)
            {
                float d2 = (x - px) * (x - px) + (z - pz) * (z - pz);
                float w = 1f / Mathf.Max(.25f, d2);
                sum += w * h; weights += w;
            }
            foreach (var p in layout.pads) Add(p.x, p.z, p.height);
            foreach (var p in layout.heightPoints ?? new HeightPoint[0]) Add(p.x, p.z, p.height);
            return weights > 0 ? sum / weights : 0;
        }

        // The territory hollow: a flat yard (the lowest height point) out to 15 m from the centre, rising over the next
        // 13 m to an uneven rim. The rim height wanders between the outer height points' range, so the skyline has
        // low saddles and higher shoulders instead of separate domes.
        static float Bowl(Layout layout, float x, float z)
        {
            var a = layout.bounds;
            float cx = a.minX + a.sizeX / 2, cz = a.minZ + a.sizeZ / 2, dx = Mathf.Abs(x - cx), dz = Mathf.Abs(z - cz);
            float r = Mathf.Pow(Mathf.Pow(dx, 4) + Mathf.Pow(dz, 4), .25f);   // a rounded square, like the bounds
            var points = layout.heightPoints ?? new HeightPoint[0];
            float floor = points.Length > 0 ? points.Min(p => p.height) : 0, top = points.Length > 0 ? points.Max(p => p.height) : 6;
            float angle = Mathf.Atan2(z - cz, x - cx), wander = Mathf.PerlinNoise(Mathf.Cos(angle) * 1.6f + 40f, Mathf.Sin(angle) * 1.6f + 7.5f);   // no seam where the angle wraps
            float rim = Mathf.Lerp(top * .65f, top, wander);
            // A saddle in the south rim where the path leaves through the wicker gate.
            float fromSouth = Mathf.Abs(Mathf.DeltaAngle(angle * Mathf.Rad2Deg, -90f));
            rim = Mathf.Lerp(floor + .6f, rim, Smooth(6f, 30f, fromSouth));
            return Mathf.Lerp(floor, rim, Smooth(15f, 28f, r));
        }

        // Signed distance to the road union (negative inside), and the centre-line height nearest to the point.
        public static float RoadDistance(Layout layout, float x, float z, out float centreHeight)
        {
            var nodes = layout.nodes.ToDictionary(n => n.id);
            float best = float.MaxValue; centreHeight = 0;
            foreach (var edge in layout.edges)
            {
                Node a = nodes[edge.from], b = nodes[edge.to];
                var ab = new Vector2(b.x - a.x, b.z - a.z);
                var ap = new Vector2(x - a.x, z - a.z);
                float t = ab.sqrMagnitude < .0001f ? 0 : Mathf.Clamp01(Vector2.Dot(ap, ab) / ab.sqrMagnitude);
                float d = (ap - ab * t).magnitude - edge.width * .5f;
                if (d >= best) continue;
                best = d;
                centreHeight = BaseHeight(layout, a.x + ab.x * t, a.z + ab.y * t);
            }
            return best;
        }

        // Signed distance to the nearest pad (negative inside). Paint uses rounded corners so pads don't read as
        // rectangles; the height platform itself stays rectangular.
        public static float PadDistance(Layout layout, float x, float z, out Pad nearest, float cornerRadius = 0)
        {
            float best = float.MaxValue; nearest = null;
            foreach (var p in layout.pads)
            {
                float r = Mathf.Min(cornerRadius, Mathf.Min(p.halfX, p.halfZ));
                float qx = Mathf.Abs(x - p.x) - (p.halfX - r), qz = Mathf.Abs(z - p.z) - (p.halfZ - r);
                float d = new Vector2(Mathf.Max(qx, 0), Mathf.Max(qz, 0)).magnitude + Mathf.Min(Mathf.Max(qx, qz), 0) - r;
                if (d < best) { best = d; nearest = p; }
            }
            return best;
        }

        // K5: one gentle height field shared by the whole world. Every block blends to it over its outer 12 m, so
        // two neighbouring blocks meet at exactly the same height with no seam or cliff.
        public static float WorldBase(float x, float z) =>
            .7f + 1.1f * (Mathf.PerlinNoise(x * .011f + 3.3f, z * .011f + 8.1f) - .5f);

        // Where a spot sits in the land (tree placement, ground colour): relief is its height above the mean of a ring
        // `ring` metres round it (knolls and rims positive, hollows negative); slope is rise over run.
        public static (float relief, float slope) Site(Layout layout, float x, float z, float ring = 12f)
        {
            float h = Height(layout, x, z), mean = 0;
            for (int k = 0; k < 8; k++) mean += Height(layout, x + Mathf.Cos(k * .785f) * ring, z + Mathf.Sin(k * .785f) * ring);
            float dx = Height(layout, x + 1.5f, z) - Height(layout, x - 1.5f, z), dz = Height(layout, x, z + 1.5f) - Height(layout, x, z - 1.5f);
            return (h - mean / 8, new Vector2(dx, dz).magnitude / 3f);
        }

        public static float Height(Layout layout, float x, float z)
        {
            float h = BaseHeight(layout, x, z)
                + layout.noise * 2f * (Mathf.PerlinNoise(x * .05f + 11f, z * .05f + 7f) - .5f)
                + layout.noise * (Mathf.PerlinNoise(x * .17f + 53f, z * .17f + 29f) - .5f)
                // Ground grain: hummocks and hollows a few metres across, so light and shade break up the slopes.
                + .4f * (Mathf.PerlinNoise(x * .22f + 401f, z * .22f + 77f) - .5f)
                + .16f * (Mathf.PerlinNoise(x * .7f + 13f, z * .7f + 211f) - .5f);
            // Broad relief: two octaves of rolling hills; on terraced ground the slopes break into soft steps.
            if (layout.relief > 0)
            {
                // Warp the sample point so hills bend into spurs and hollows instead of round domes, and add a
                // ridged octave so the high ground runs in crests with shoulders falling away on either side.
                float wx = x + 14f * (Mathf.PerlinNoise(x * .012f + 7f, z * .012f + 3f) - .5f), wz = z + 14f * (Mathf.PerlinNoise(x * .012f + 41f, z * .012f + 19f) - .5f);
                float ridge = 1f - Mathf.Abs(Mathf.PerlinNoise(wx * .026f + 211f, wz * .026f + 97f) * 2f - 1f);
                float hill = (Mathf.PerlinNoise(wx * .018f + 101f, wz * .018f + 57f) - .5f) * 2f * .55f + (ridge * ridge - .35f) * .55f
                    + (Mathf.PerlinNoise(wx * .06f + 13f, wz * .06f + 91f) - .5f) * 2f * .2f;
                float rise = hill * layout.relief;
                if (layout.terrace > 0)
                {
                    float steps = rise / layout.terrace, floor = Mathf.Floor(steps), t = steps - floor;
                    rise = Mathf.Lerp(rise, (floor + Mathf.SmoothStep(0, 1, Mathf.Clamp01((t - .5f) / .5f))) * layout.terrace, .35f);   // soft shelves, not sawtooth
                }
                // Escarpments (z1nnz 2026-10-31, the reference valleys): the land breaks into two shelves with steep
                // grey rock walls between them, the rim wandering in bays and spurs. Roads, pads and the creek cut
                // through them afterwards, so every way stays walkable.
                if (layout.cliffs > 0)
                {
                    float n = Mathf.PerlinNoise(wx * .016f + 301f, wz * .016f + 77f) + .22f * (Mathf.PerlinNoise(wx * .07f + 9f, wz * .07f + 5f) - .5f);
                    float lower = Smooth(.48f, .52f, n), upper = Smooth(.665f, .695f, n);
                    // Near a road or a pad the wall softens into a ramp, so a way climbs from shelf to shelf instead of
                    // running in a cut between two walls.
                    float near = Mathf.Min(RoadDistance(layout, x, z, out _), PadDistance(layout, x, z, out _, 3.5f));
                    float amp = layout.cliffs * Smooth(1.5f, 8f, near);
                    lower = Mathf.Lerp(Smooth(.38f, .62f, n), lower, Smooth(3f, 8f, near));
                    upper = Mathf.Lerp(Smooth(.6f, .76f, n), upper, Smooth(3f, 8f, near));
                    rise += (lower + upper * .6f - .5f) * amp;
                    // The wall itself is not a smooth ramp: rock strata and ledges across its face.
                    float face = (4f * lower * (1f - lower) + 4f * upper * (1f - upper)) * Smooth(3f, 8f, near);
                    rise += face * (.45f * (Mathf.PerlinNoise(wx * .35f + 17f, wz * .35f + 3f) - .5f) + .2f * Mathf.Sin(rise * 4.2f));
                }
                h += rise;
            }
            float road = RoadDistance(layout, x, z, out float roadHeight);
            h = Mathf.Lerp(roadHeight, h, Smooth(0f, RoadBlend, road));
            var area = layout.bounds;
            float border = Mathf.Min(Mathf.Min(x - area.minX, area.minX + area.sizeX - x), Mathf.Min(z - area.minZ, area.minZ + area.sizeZ - z));
            if (!layout.isolated) h = Mathf.Lerp(WorldBase(x, z), h, Smooth(1f, 12f, border));
            // Creek: a flat bed (depth below the land at the centre line) easing up the banks.
            float creek = CreekDistance(layout, x, z, out float creekLand);
            if (!float.IsPositiveInfinity(creek))
            {
                var c = layout.creek;
                float bed = creekLand - c.depth + .05f * (Mathf.PerlinNoise(x * .4f, z * .4f) - .5f);
                // D3: the river tiles (PR #45) are 7 m wide and level across, so the corridor under them is a flat
                // shelf at the centre-line land (no noise, no side slope) that eases back into the hillside.
                if (layout.creekKit != null && layout.creekKit.Length > 0)
                    h = Mathf.Lerp(creekLand, h, Smooth(c.width * .5f + c.bank + .6f, c.width * .5f + c.bank + 4.6f, creek));
                h = Mathf.Lerp(bed, h, Smooth(c.width * .35f, c.width * .5f + c.bank, creek));
            }
            // Levelled strips under works that cross the creek bank (joshsu54's old channel): after the creek, so the
            // intake end reaches into the water at its stated height.
            foreach (var f in layout.flats ?? new Flat[0])
            {
                float edge = Mathf.Max(Mathf.Abs(x - f.x) - f.halfX, Mathf.Abs(z - f.z) - f.halfZ);
                h = Mathf.Lerp(f.height, h, Smooth(0f, f.blend, edge));
            }
            // Pads last: each zone stands on one flat platform at its stated height. The edge wanders so the platform
            // is not a box cut into the hill, and the bank around it is wider the more it has to climb or fall, so it
            // stays a slope you could walk (about 1 in 2) instead of a cut wall.
            foreach (var p in layout.pads)
            {
                float wobble = (Mathf.PerlinNoise(x * .21f + p.x * .37f, z * .21f + p.z * .37f) - .5f) * 2.2f;
                float edge = Mathf.Max(Mathf.Abs(x - p.x) - p.halfX, Mathf.Abs(z - p.z) - p.halfZ) + wobble;
                float blend = Mathf.Max(PadBlend, Mathf.Abs(p.height - h) * 2.2f);
                h = Mathf.Lerp(p.height, h, Smooth(0f, blend, edge));
            }
            return h;
        }

        /// <summary>World-space ground height under (x, z) on the generated terrain.</summary>
        public static float Ground(Terrain terrain, float x, float z) =>
            terrain.SampleHeight(new Vector3(x, 0, z)) + terrain.transform.position.y;

        public static Terrain Create(Transform parent) => Create(parent, Load(), "NoviceVillageTerrain", "NoviceVillageTerrain (route data)");

        public static Terrain Create(Transform parent, Layout layout, string asset, string objectName)
        {
            var area = layout.bounds;
            var data = AssetDatabase.LoadAssetAtPath<TerrainData>(Generated + "/" + asset + ".asset");
            if (data == null)
            {
                data = new TerrainData();
                AssetDatabase.CreateAsset(data, Generated + "/" + asset + ".asset");
            }
            data.heightmapResolution = HeightResolution;
            data.size = new Vector3(area.sizeX, HeightRange, area.sizeZ);
            var heights = new float[HeightResolution, HeightResolution];
            for (int z = 0; z < HeightResolution; z++)
            for (int x = 0; x < HeightResolution; x++)
            {
                float wx = area.minX + x * area.sizeX / (HeightResolution - 1);
                float wz = area.minZ + z * area.sizeZ / (HeightResolution - 1);
                heights[z, x] = Mathf.Clamp01((Height(layout, wx, wz) - BaseY) / HeightRange);
            }
            data.SetHeights(0, 0, heights);
            // Relief on a coarse grid (every 8 samples, ~1.6 m on a 100 m block): height above the mean of the ground
            // about 10 m round, in metres; read back bilinearly for the paint.
            const int C = (HeightResolution - 1) / 8 + 1;
            var coarse = new float[C, C];
            for (int z = 0; z < C; z++) for (int x = 0; x < C; x++) coarse[z, x] = heights[z * 8, x * 8] * HeightRange;
            var reliefGrid = new float[C, C];
            const int Ring = 6;
            for (int z = 0; z < C; z++)
            for (int x = 0; x < C; x++)
            {
                float sum = 0; int n = 0;
                for (int dz = -Ring; dz <= Ring; dz += 2)
                for (int dx = -Ring; dx <= Ring; dx += 2)
                {
                    int zz = Mathf.Clamp(z + dz, 0, C - 1), xx = Mathf.Clamp(x + dx, 0, C - 1);
                    sum += coarse[zz, xx]; n++;
                }
                reliefGrid[z, x] = coarse[z, x] - sum / n;
            }
            float ReliefAt(float u, float v)   // u, v in 0..1 across the block
            {
                float fx = u * (C - 1), fz = v * (C - 1);
                int x0 = Mathf.Clamp((int)fx, 0, C - 2), z0 = Mathf.Clamp((int)fz, 0, C - 2);
                float tx = fx - x0, tz = fz - z0;
                return Mathf.Lerp(Mathf.Lerp(reliefGrid[z0, x0], reliefGrid[z0, x0 + 1], tx), Mathf.Lerp(reliefGrid[z0 + 1, x0], reliefGrid[z0 + 1, x0 + 1], tx), tz);
            }

            data.terrainLayers = Layers();
            data.alphamapResolution = PaintResolution;
            var paint = new float[PaintResolution, PaintResolution, LayerNames.Length];
            var detail = new int[PaintResolution, PaintResolution];
            var cover = new float[PaintResolution, PaintResolution];   // how much grass belongs here (0..1)
            var dryness = new float[PaintResolution, PaintResolution];
            var edgeOf = new float[PaintResolution, PaintResolution];  // near a pad, road or rock: taller grass
            var pathEdge = new float[PaintResolution, PaintResolution];   // the worn edge of a path or the creek bank: pebbles
            for (int z = 0; z < PaintResolution; z++)
            for (int x = 0; x < PaintResolution; x++)
            {
                float wx = area.minX + (x + .5f) * area.sizeX / PaintResolution;
                float wz = area.minZ + (z + .5f) * area.sizeZ / PaintResolution;
                float edgeNoise = (Mathf.PerlinNoise(wx * .36f + 7f, wz * .36f + 3f) - .5f) * .6f;
                float road = RoadDistance(layout, wx, wz, out _);
                float pad = PadDistance(layout, wx, wz, out var nearest, 3.5f) + edgeNoise * 1.5f;
                float inPad = 1f - Smooth(-1.2f, .6f, pad);
                // Irregular paths: the worn width wanders along the road and the edge is ragged, grass creeping in.
                float wander = (Mathf.PerlinNoise(wx * .09f + 211f, wz * .09f + 17f) - .5f) * 1.1f;
                float ragged = (Mathf.PerlinNoise(wx * 1.3f + 5f, wz * 1.3f + 77f) - .5f) * .55f;
                float worn = road + wander + ragged;
                float dirt = Mathf.Max(1f - Smooth(-.35f, .9f, worn), nearest?.surface == "dirt" ? inPad * .7f : 0);
                // Stone slabs on the village roads (A1 only), broken into stretches with earth between them.
                bool village = area.minX == -50 && area.minZ == -50;
                float slabRun = Smooth(.55f, .7f, Mathf.PerlinNoise(wx * .06f + 300f, wz * .06f + 300f));
                float slabs = village ? dirt * slabRun * (1f - Smooth(-.9f, .2f, worn + .4f)) : 0;
                float plaza = Mathf.Max(nearest?.surface == "plaza" ? inPad * .85f : 0, slabs);
                float forest = nearest?.surface == "forest" ? (1f - Smooth(-1f, 3f, pad)) * (1f - dirt) : 0;
                // Creek banks: gravel at the water's edge, darker leaf-litter and moss further up the bank.
                float creek = CreekDistance(layout, wx, wz, out _);
                float gravel = 0;
                if (layout.creek != null)
                {
                    float half = layout.creek.width * .5f;
                    gravel = (1f - Smooth(half + .2f, half + 1.6f, creek + edgeNoise * 2f)) * (1f - dirt);
                    forest = Mathf.Max(forest, (1f - Smooth(half + 1f, half + layout.creek.bank + 2.5f, creek + edgeNoise * 3f)) * (1f - dirt) * (1f - gravel));
                }
                // Steep ground shows the warm ochre rock; open meadow alternates lush and sun-dried patches.
                float step = area.sizeX / PaintResolution;
                float slope = Mathf.Max(Mathf.Abs(Height(layout, wx + step, wz) - Height(layout, wx - step, wz)), Mathf.Abs(Height(layout, wx, wz + step) - Height(layout, wx, wz - step))) / (2 * step);
                // Rock shows only where the ground is really steep, in outcrops (not along every bank); moderate
                // banks are bare earth broken by grass.
                float outcrop = Smooth(.4f, .6f, Mathf.PerlinNoise(wx * .09f + 13f, wz * .09f + 57f));
                float rock = (layout.isolated ? Smooth(.85f, 1.2f, slope + edgeNoise * .3f) : Mathf.Max(Smooth(.62f, .95f, slope + edgeNoise * .3f) * outcrop, Smooth(.9f, 1.3f, slope + edgeNoise * .2f))) * (1f - dirt);   // the hollow's slopes stay grassy; walls are rock
                float bank = layout.isolated ? 0 : Smooth(.32f, .62f, slope + edgeNoise * .25f) * Smooth(.35f, .65f, Mathf.PerlinNoise(wx * .23f + 91f, wz * .23f + 3f)) * (1f - rock) * (1f - dirt) * .75f;
                dirt = Mathf.Max(dirt, bank);
                float dryPatch = Smooth(.46f, .72f, Mathf.PerlinNoise(wx * .03f + 71f, wz * .03f + 9f) * .7f + Mathf.PerlinNoise(wx * .22f + 5f, wz * .22f + 33f) * .3f + edgeNoise * .3f);
                // The land decides most of it: tops and shoulders catch the sun (light warm meadow), hollows hold water
                // and stay deep green; the noise only breaks the edges.
                float landRelief = ReliefAt((x + .5f) / PaintResolution, (z + .5f) / PaintResolution);
                float sunlit = Smooth(.1f, 1.1f, landRelief + edgeNoise * .4f), hollow = Smooth(.2f, 1.2f, -landRelief);
                dryPatch = Mathf.Clamp01(dryPatch * .35f + sunlit * .8f) * (1f - hollow * .85f);
                plaza *= 1f - dirt * .5f;
                float open = Mathf.Max(0, 1f - dirt - plaza - forest - gravel - rock);
                paint[z, x, 1] = dirt;
                paint[z, x, 2] = plaza;
                paint[z, x, 3] = forest;
                paint[z, x, 5] = gravel;
                paint[z, x, 6] = rock;
                paint[z, x, 4] = open * dryPatch * .85f;
                paint[z, x, 0] = Mathf.Max(.01f, open - paint[z, x, 4]);
                float sum = 0;
                for (int l = 0; l < LayerNames.Length; l++) sum += paint[z, x, l];
                for (int l = 0; l < LayerNames.Length; l++) paint[z, x, l] /= sum;
                // Grass: none on roads or pads, thinning toward their edges.
                float density = Smooth(.1f, 1.8f, worn) * Smooth(.5f, 2.5f, pad) * (1f - rock) * (1f - gravel)
                    * (layout.creek != null ? Smooth(layout.creek.width * .5f + .5f, layout.creek.width * .5f + 2.5f, creek) : 1f);
                float scatter = Mathf.PerlinNoise(wx * .71f + 31f, wz * .71f + 41f);
                detail[z, x] = density > .7f && scatter > .42f ? (scatter > .66f ? 4 : scatter > .54f ? 2 : 1) : 0;
                cover[z, x] = density;
                pathEdge[z, x] = Mathf.Max(1f - Mathf.Abs(worn - .6f) / 1.1f, layout.creek != null ? 1f - Mathf.Abs(creek - layout.creek.width * .5f - .8f) / 1.5f : 0);
                dryness[z, x] = dryPatch;
                edgeOf[z, x] = Mathf.Max(1f - Smooth(2.5f, 6f, Mathf.Min(pad, worn)), Smooth(.25f, .5f, slope));
            }
            data.SetAlphamaps(0, 0, paint);

            // Meadow (QingxiGroundKit): stands of grass with turf between them (about a third of the ground), lush or sun-dried by patch,
            // taller along paths, platforms and rock, and flowers in drifts (white, yellow or blue by area).
            const int D = PaintResolution / 2;
            var kinds = QingxiGroundKit.Prototypes();
            var layers = new int[kinds.Length][,];
            for (int k = 0; k < layers.Length; k++) layers[k] = new int[D, D];
            var rnd = new System.Random((int)(area.minX * 7 + area.minZ * 13));
            for (int z = 0; z < D; z++)
            for (int x = 0; x < D; x++)
            {
                // Stones first: pebbles along path edges and creek banks, a few mossy stones out in the meadow.
                float edge = pathEdge[z * 2, x * 2];
                if (edge > 0 && rnd.NextDouble() < .035 * edge) { layers[6][z, x] = 1; continue; }
                if (cover[z * 2, x * 2] > .5f && rnd.NextDouble() < .0015) { layers[7][z, x] = 1; continue; }
                float c = cover[z * 2, x * 2];
                if (c < .3f) continue;
                float wx = area.minX + (x + .5f) * area.sizeX / D, wz = area.minZ + (z + .5f) * area.sizeZ / D;
                double r = rnd.NextDouble();
                float drift = Mathf.PerlinNoise(wx * .12f + 5f, wz * .12f + 9f);
                if (drift > .64f && r < .32f * c)
                {
                    float hue = Mathf.PerlinNoise(wx * .04f + 31f, wz * .04f + 2f);
                    layers[hue < .42f ? 3 : hue < .62f ? 4 : 5][z, x] = 1;
                }
                // Grass grows in stands (painted turf shows between them), thicker along edges and banks.
                else if (r < .45f * c * Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.35f, .75f, Mathf.PerlinNoise(wx * .06f + 77f, wz * .06f + 15f) + edgeOf[z * 2, x * 2] * .15f)))
                {
                    int kind = dryness[z * 2, x * 2] > .55f ? 2 : edgeOf[z * 2, x * 2] > .7f && rnd.NextDouble() < .2 ? 1 : 0;
                    layers[kind][z, x] = 1;
                }
            }
            data.SetDetailScatterMode(DetailScatterMode.InstanceCountMode);
            data.SetDetailResolution(D, 16);
            data.detailPrototypes = kinds;
            for (int k = 0; k < kinds.Length; k++) data.SetDetailLayer(0, 0, k, layers[k]);
            EditorUtility.SetDirty(data);

            var go = Terrain.CreateTerrainGameObject(data);
            go.name = objectName;
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(area.minX, BaseY, area.minZ);
            var terrain = go.GetComponent<Terrain>();
            terrain.heightmapPixelError = 4;
            terrain.basemapDistance = 70;
            terrain.detailObjectDistance = 80; terrain.detailObjectDensity = 1;
            terrain.materialTemplate = AssetDatabase.LoadAssetAtPath<Material>("Packages/com.unity.render-pipelines.universal/Runtime/Materials/TerrainLit.mat");
            AssetDatabase.SaveAssets();
            Debug.Log($"QINGXI_VILLAGE_TERRAIN: {area.sizeX}x{area.sizeZ} m, height {data.bounds.min.y + BaseY:F2}..{data.bounds.max.y + BaseY:F2} m, meadow clumps {layers.Sum(l => l.Cast<int>().Sum())}");
            return terrain;
        }

        static TerrainLayer[] Layers()
        {
            var result = new TerrainLayer[LayerNames.Length];
            for (int i = 0; i < result.Length; i++)
            {
                string path = Generated + "/TerrainLayer-" + LayerNames[i] + ".asset";
                var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
                if (layer == null) { layer = new TerrainLayer(); AssetDatabase.CreateAsset(layer, path); }
                // Hand-painted textures (art/references/ground-textures-v1, generated from the style guide's
                // prompts) where we have them; the procedural ones otherwise (the village flagstones).
                float[] paintedRelief = null, relief;
                var painted = Painted[i] != null ? PaintedTexture(Painted[i], out paintedRelief) : null;
                if (painted != null) { layer.diffuseTexture = painted; relief = paintedRelief; }
                else layer.diffuseTexture = Texture(LayerNames[i], Colors[i], 20261029 + i, Kinds[i], out relief);
                layer.normalMapTexture = NormalMap(LayerNames[i], relief, Kinds[i] == "slab" || Kinds[i] == "rock" ? 2.2f : Kinds[i] == "grass" ? .8f : 1.6f);
                float tile = painted != null ? PaintedTile[i] : Tiles[i];
                layer.tileSize = new Vector2(tile, tile);
                // The sun-dried meadow is the meadow painting, warmed toward straw.
                layer.diffuseRemapMin = Vector4.zero;
                layer.diffuseRemapMax = LayerNames[i] == "MeadowDry" ? new Vector4(1.02f, 1.0f, .6f, 1) : LayerNames[i] == "OchreRock" ? new Vector4(.6f, .66f, .76f, 1) : LayerNames[i] == "VillageMeadow" ? new Vector4(.78f, .86f, .7f, 1) : Vector4.one;
                layer.smoothness = 0; layer.metallic = 0;
                EditorUtility.SetDirty(layer);
                result[i] = layer;
            }
            return result;
        }

        // Soil under the trees (z1nnz 2026-10-31: 地面也要按照樹種有不同的土壤): every species drops its own litter and
        // keeps its own ground under its crown, the edge ragged and fading into the meadow, paths and stones left as
        // they are, and the grass thinner in the shade. Painted soil-<name>.png from art/references/ground-textures-v1
        // (prompts in soil-prompts.md) when it is there; until then a tinted painting stands in.
        static readonly System.Collections.Generic.Dictionary<string, (string soil, float reach)> SoilOfKind = new System.Collections.Generic.Dictionary<string, (string, float)> {
            ["ElderCamphor"] = ("camphor", .45f), ["ElderMaple"] = ("maple", .55f), ["ElderGinkgo"] = ("ginkgo", .38f),
            ["ElderPine"] = ("needle", .4f), ["ElderCypress"] = ("needle", .38f), ["ElderWillow"] = ("willow", .42f),
            ["ElderPlum"] = ("plum", .5f), ["ElderWithered"] = ("withered", .45f), ["ElderGuardian"] = ("jianmu", .7f), ["JianmuSapling"] = ("jianmu", .9f) };
        // Stand-in until the painting exists: which painting, warmed or cooled toward the soil's colour.
        static readonly System.Collections.Generic.Dictionary<string, (string painting, Vector4 tint)> SoilStandIn = new System.Collections.Generic.Dictionary<string, (string, Vector4)> {
            ["camphor"] = ("ground-forest", new Vector4(.8f, .9f, .74f, 1)), ["maple"] = ("ground-forest", new Vector4(1.12f, .82f, .62f, 1)),
            ["ginkgo"] = ("ground-forest", new Vector4(1.18f, 1.06f, .62f, 1)), ["needle"] = ("ground-forest", new Vector4(.9f, .82f, .64f, 1)),
            ["willow"] = ("ground-forest", new Vector4(.7f, .84f, .66f, 1)), ["plum"] = ("ground-meadow", new Vector4(.98f, .9f, .86f, 1)),
            ["withered"] = ("ground-path", new Vector4(1.04f, .98f, .86f, 1)), ["jianmu"] = ("ground-forest", new Vector4(.58f, .88f, .56f, 1)) };

        public static string SoilKind(string treeName) => SoilOfKind.Keys.Where(k => treeName.StartsWith(k)).OrderByDescending(k => k.Length).FirstOrDefault();

        static TerrainLayer SoilLayer(string soil)
        {
            string path = Generated + "/TerrainLayer-Soil-" + soil + ".asset";
            var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
            if (layer == null) { layer = new TerrainLayer(); AssetDatabase.CreateAsset(layer, path); }
            var painted = PaintedTexture("soil-" + soil, out var relief);
            var tint = Vector4.one;
            if (painted == null) { painted = PaintedTexture(SoilStandIn[soil].painting, out relief); tint = SoilStandIn[soil].tint; }
            layer.diffuseTexture = painted;
            layer.normalMapTexture = NormalMap("Soil-" + soil, relief, 1.6f);
            layer.tileSize = new Vector2(2.5f, 2.5f);
            layer.diffuseRemapMin = Vector4.zero; layer.diffuseRemapMax = tint;
            layer.smoothness = 0; layer.metallic = 0;
            EditorUtility.SetDirty(layer);
            return layer;
        }

        // trees: position (layout x/z), height in metres, and the tree's model name (ElderMaple_B ...).
        public static void PaintSoils(Terrain terrain, System.Collections.Generic.IList<(Vector2 at, float height, string name)> trees)
        {
            var data = terrain.terrainData;
            var under = trees.Select(t => (t.at, t.height, kind: SoilKind(t.name))).Where(t => t.kind != null).ToList();
            if (under.Count == 0) return;
            var layers = data.terrainLayers.ToList();
            var index = new System.Collections.Generic.Dictionary<string, int>();
            foreach (var soil in under.Select(t => SoilOfKind[t.kind].soil).Distinct())
            {
                var layer = SoilLayer(soil);
                int at = layers.IndexOf(layer);
                if (at < 0) { layers.Add(layer); at = layers.Count - 1; }
                index[soil] = at;
            }
            int res = data.alphamapResolution, old = data.alphamapLayers;
            var before = data.GetAlphamaps(0, 0, res, res);
            data.terrainLayers = layers.ToArray();
            var paint = new float[res, res, layers.Count];
            for (int z = 0; z < res; z++) for (int x = 0; x < res; x++) for (int l = 0; l < old; l++) paint[z, x, l] = before[z, x, l];
            var shade = new float[res, res];
            Vector3 origin = terrain.transform.position, size = data.size;
            foreach (var t in under)
            {
                var (soil, reach) = SoilOfKind[t.kind];
                float r = Mathf.Max(2.5f, t.height * reach);
                int x0 = Mathf.Max(0, (int)((t.at.x - r - origin.x) / size.x * res)), x1 = Mathf.Min(res - 1, (int)((t.at.x + r - origin.x) / size.x * res));
                int z0 = Mathf.Max(0, (int)((t.at.y - r - origin.z) / size.z * res)), z1 = Mathf.Min(res - 1, (int)((t.at.y + r - origin.z) / size.z * res));
                int li = index[soil];
                for (int z = z0; z <= z1; z++)
                for (int x = x0; x <= x1; x++)
                {
                    float wx = origin.x + (x + .5f) * size.x / res, wz = origin.z + (z + .5f) * size.z / res;
                    float d = Vector2.Distance(new Vector2(wx, wz), t.at);
                    // Ragged edge: litter blows out further on one side, meadow creeps in on another.
                    float ragged = (Mathf.PerlinNoise(wx * .35f + t.at.x, wz * .35f + t.at.y) - .5f) * r * .6f;
                    float w = (1f - Smooth(r * .15f, r * 1.1f, d + ragged)) * .75f;   // wide and soft-edged: never a disc
                    if (w <= 0) continue;
                    // Paths, flagstones, creek gravel and rock stay as they are.
                    float keep = paint[z, x, 1] + paint[z, x, 2] + paint[z, x, 5] + paint[z, x, 6];
                    w *= Mathf.Clamp01(1f - keep * 1.5f);
                    for (int l = 0; l < layers.Count; l++) paint[z, x, l] *= 1f - w;
                    paint[z, x, li] += w;
                    shade[z, x] = Mathf.Max(shade[z, x], w);
                }
            }
            data.SetAlphamaps(0, 0, paint);
            // Thinner grass and fewer flowers in the shade (prototypes 0-5; the stones, 6 and 7, stay).
            int D = data.detailResolution;
            var rnd = new System.Random(res + under.Count);
            for (int k = 0; k < Mathf.Min(6, data.detailPrototypes.Length); k++)
            {
                var grid = data.GetDetailLayer(0, 0, D, D, k);
                for (int z = 0; z < D; z++)
                for (int x = 0; x < D; x++)
                {
                    if (grid[z, x] == 0) continue;
                    float s = shade[Mathf.Min(res - 1, z * res / D), Mathf.Min(res - 1, x * res / D)];
                    if (rnd.NextDouble() < s * (k >= 3 ? .85f : .6f)) grid[z, x] = 0;
                }
                data.SetDetailLayer(0, 0, k, grid);
            }
            EditorUtility.SetDirty(data);
            Debug.Log($"QINGXI_SOIL: {under.Count} trees, soils {string.Join(", ", index.Keys)}, {layers.Count} terrain layers");
        }

        // Painted texture per layer (null = procedural) and its tile size in metres (the scale the prompt asked for).
        static readonly string[] Painted = { "ground-meadow", "ground-path", null, "ground-forest", "ground-meadow", "ground-gravel", "ground-rock" };
        static readonly float[] PaintedTile = { 3, 2.5f, 4, 2.5f, 3, 1.8f, 3.5f };
        const string PaintedFolder = "Assets/YunJing/Models/GroundTexturesV1";   // copied from art/references, gitignored

        static Texture2D PaintedTexture(string name, out float[] relief)
        {
            relief = null;
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            string src = Path.Combine(repo, "art/references/ground-textures-v1", name + ".png");
            if (!File.Exists(src) || new FileInfo(src).Length < 1024) return null;
            string dstDir = Path.Combine(repo, "apps/game", PaintedFolder);
            Directory.CreateDirectory(dstDir);
            string dst = Path.Combine(dstDir, name + ".png");
            if (!File.Exists(dst) || new FileInfo(dst).Length != new FileInfo(src).Length) { File.Copy(src, dst, true); AssetDatabase.Refresh(); }
            string asset = PaintedFolder + "/" + name + ".png";
            var ti = (TextureImporter)AssetImporter.GetAtPath(asset);
            if (ti != null && (ti.wrapMode != TextureWrapMode.Repeat || ti.maxTextureSize != 2048 || ti.anisoLevel != 4))
            {
                ti.wrapMode = TextureWrapMode.Repeat; ti.maxTextureSize = 2048; ti.anisoLevel = 4; ti.mipmapEnabled = true; ti.sRGBTexture = true;
                ti.SaveAndReimport();
            }
            // Relief for the normal map from the painting's brightness (stones and clumps light, gaps dark), at 512 px.
            var tmp = new Texture2D(2, 2);
            tmp.LoadImage(File.ReadAllBytes(src));
            const int N = 512;
            relief = new float[N * N];
            for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                var c = tmp.GetPixelBilinear((x + .5f) / N, (y + .5f) / N);
                relief[y * N + x] = c.r * .3f + c.g * .55f + c.b * .15f;
            }
            UnityEngine.Object.DestroyImmediate(tmp);
            return AssetDatabase.LoadAssetAtPath<Texture2D>(asset);
        }

        // A tileable ground texture drawn from noise: every kind has its own pattern so the ground reads as grass,
        // earth, slabs, leaf litter, gravel or rock up close, not as one flat colour. `relief` is the matching height
        // field (raised slabs and pebbles, sunken joints) for the normal map.
        static Texture2D Texture(string name, Color color, int seed, string kind, out float[] relief)
        {
            int N = kind == "slab" || kind == "gravel" ? 512 : 256;
            string path = Generated + "/Terrain-" + name + ".asset";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null || texture.width != N)
            {
                if (texture != null) AssetDatabase.DeleteAsset(path);
                texture = new Texture2D(N, N, TextureFormat.RGBA32, true) { name = "Terrain-" + name };
                AssetDatabase.CreateAsset(texture, path);
            }
            var rng = new System.Random(seed);
            float ox = rng.Next(1000), oz = rng.Next(1000);
            // Tileable noise: blend four copies shifted by one tile, so opposite edges meet without bending the pattern.
            float Tile(float u, float v, float freq)
            {
                float Nz(float x, float y) => Mathf.PerlinNoise(ox + x * freq, oz + y * freq);
                return Nz(u, v) * (1 - u) * (1 - v) + Nz(u - 1, v) * u * (1 - v) + Nz(u, v - 1) * (1 - u) * v + Nz(u - 1, v - 1) * u * v;
            }
            float Fbm(float u, float v, float f) => Tile(u, v, f) * .55f + Tile(u, v, f * 2.1f) * .3f + Tile(u, v, f * 4.3f) * .15f;
            // Cell centres (wrapping) for pebbles, slabs and leaves; z is the cell's own shade. Slabs are jittered off
            // a loose grid so they are irregular but similar in size, like laid flagstones.
            int count = kind == "gravel" ? 240 : 70;
            Vector3[] cells;
            if (kind == "slab")
            {
                int g = 10; cells = new Vector3[g * 11];
                for (int i = 0; i < cells.Length; i++)
                    cells[i] = new Vector3(((i % g) + .5f + ((float)rng.NextDouble() - .5f) * .8f) / g, ((i / g) + .5f + ((float)rng.NextDouble() - .5f) * .8f) / 11f, (float)rng.NextDouble());
            }
            else cells = Enumerable.Range(0, count).Select(_ => new Vector3((float)rng.NextDouble(), (float)rng.NextDouble(), (float)rng.NextDouble())).ToArray();
            for (int i = 0; i < cells.Length; i++) cells[i] = new Vector3(Mathf.Repeat(cells[i].x, 1), Mathf.Repeat(cells[i].y, 1), cells[i].z);
            float Distance(float u, float v, Vector3 k)
            {
                float du = Mathf.Abs(u - k.x), dv = Mathf.Abs(v - k.y); du = Mathf.Min(du, 1 - du); dv = Mathf.Min(dv, 1 - dv);
                return Mathf.Sqrt(du * du + dv * dv);
            }
            var pixels = new Color[N * N];
            relief = new float[N * N];
            for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float u = x / (float)N, v = y / (float)N, light = Fbm(u, v, 6) - .5f, tint = Fbm(u, v, 2.5f) - .5f;
                float d1 = 9, d2 = 9; var cell = cells[0];
                foreach (var k in cells) { float d = Distance(u, v, k); if (d < d1) { d2 = d1; d1 = d; cell = k; } else if (d < d2) d2 = d; }
                Color c = color; float h = .5f + light * .3f;
                float crack = Mathf.SmoothStep(0, 1, Mathf.Clamp01((d2 - d1) / .01f));   // 0 on a cell boundary
                switch (kind)
                {
                    case "grass":   // fine speckle of blades in every direction, darker tufts, a warmer hue in places
                        // Painted turf: patches of darker and lighter green the size of a hand, short directional strokes
                        // (blades lying in the wind), clover dots, and soil showing through in a few places.
                        float patch = Fbm(u, v, 9) - .5f, speck = Tile(u, v, 64) - .5f;
                        // Strokes: noise stretched along one direction (u repeated 4x keeps it tileable), not a sine (moiré).
                        float stroke = Tile(Mathf.Repeat(u * 4f, 1f), v, 26);
                        c = color * (1 + light * .35f + patch * .55f + (stroke - .5f) * .18f + speck * .12f)
                            + new Color(tint * .1f + patch * .04f, tint * .07f, -tint * .04f);
                        if (cell.z > .62f && d1 < .006f + cell.z * .004f) c = Color.Lerp(c, color * new Color(.8f, 1.2f, .75f), .6f);   // clover
                        if (Tile(u, v, 34) > .72f) c = Color.Lerp(c, new Color(.42f, .36f, .24f), .45f);   // soil showing through
                        h = .5f + patch * .7f + (stroke - .5f) * .25f + speck * .2f;
                        break;
                    case "earth":   // packed earth: clods, dry cracks, small stones and bits of grass
                        float clod = Fbm(u * 1.3f, v * 1.3f, 20) - .5f;
                        c = color * (1 + light * .4f + clod * .35f + (Tile(u, v, 90) - .5f) * .16f);
                        h = .45f + clod * .6f + light * .3f;
                        if (cell.z < .5f && Tile(u, v, 5) > .56f) { c = Color.Lerp(c * .82f, c, crack); h -= (1 - crack) * .2f; }   // dried cracks, here and there
                        if (cell.z > .35f && d1 < .003f + cell.z * .007f) { c = Color.Lerp(c, color * (1.08f + cell.z * .2f), .6f); h += .35f; }
                        if (Tile(u, v, 55) > .7f) c = Color.Lerp(c, new Color(.34f, .42f, .22f), .3f);   // grass creeping in
                        break;
                    case "slab":    // laid flagstones: each its own shade and wear, dark soft joints, moss in some of them
                        float joint = Mathf.SmoothStep(0, 1, Mathf.Clamp01((d2 - d1) / .018f));   // 0 in the joint, 1 on the stone
                        var shade = new Color(.92f + cell.z * .16f, .92f + cell.z * .12f, .9f + (1 - cell.z) * .12f);   // warm or cool stones
                        float wear = Fbm(u + cell.z, v - cell.z, 9) - .5f, grime = Tile(u, v, 30) - .5f;
                        var stone = new Color(color.r * shade.r, color.g * shade.g, color.b * shade.b) * (1 + wear * .45f + grime * .15f);
                        stone *= Mathf.Lerp(.82f, 1f, Mathf.Clamp01((d2 - d1) / .05f));   // edges worn darker
                        var gap = Tile(u, v, 22) > .58f ? new Color(.26f, .32f, .18f) : new Color(.24f, .21f, .17f);   // moss or soil in the joint
                        c = Color.Lerp(gap, stone, joint);
                        h = joint * (.75f + wear * .25f) + (1 - joint) * .1f;
                        break;
                    case "litter":  // leaf litter and moss over dark soil
                        c = color * (1 + light * .5f);
                        if (Tile(u, v, 70) > .6f) { c = Color.Lerp(c, cell.z > .5f ? new Color(.52f, .38f, .2f) : new Color(.35f, .42f, .22f), .4f); h += .2f; }   // small leaves, not camouflage blotches
                        break;
                    case "gravel":  // rounded pebbles of several greys
                        float pebble = Mathf.Clamp01((1 - d1 / (.016f + cell.z * .018f)) * 1.6f);   // 4-9 cm pebbles of mixed sizes
                        c = Color.Lerp(color * (.72f + light * .2f), color * (.85f + cell.z * .35f), pebble) * (1 + light * .2f);
                        h = Mathf.Sqrt(pebble) * .9f;
                        break;
                    case "rock":    // weathered stone: cracked blocks of different shades, grain, lichen (no stripes,
                                    // which the top-down terrain projection would stretch on steep faces)
                        float grain = Fbm(u * 1.7f, v * 1.7f, 14) - .5f;
                        c = color * (.8f + light * .35f + grain * .35f + (cell.z - .5f) * .2f);
                        c = Color.Lerp(c * .5f, c, crack);
                        if (Tile(u, v, 26) > .63f) c = Color.Lerp(c, new Color(.44f, .5f, .36f), .32f);   // lichen
                        h = crack * (.6f + grain * .5f) + cell.z * .25f;
                        break;
                }
                // URP Terrain Lit reads smoothness from the albedo alpha when there is no mask map: keep it matte.
                pixels[y * N + x] = new Color(Mathf.Clamp01(c.r), Mathf.Clamp01(c.g), Mathf.Clamp01(c.b), .06f);
                relief[y * N + x] = h;
            }
            texture.SetPixels(pixels);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.anisoLevel = 4;
            texture.Apply(true);
            EditorUtility.SetDirty(texture);
            return texture;
        }

        // Tangent-space normal map from a wrapped height field (R = x, G = y, B = z, A = 1; the URP terrain shader
        // unpacks this layout), so slab joints, pebbles and strata catch the light.
        static Texture2D NormalMap(string name, float[] relief, float strength)
        {
            int N = (int)Mathf.Sqrt(relief.Length);
            string path = Generated + "/TerrainNormal-" + name + ".asset";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null || texture.width != N)
            {
                if (texture != null) AssetDatabase.DeleteAsset(path);
                texture = new Texture2D(N, N, TextureFormat.RGBA32, true, true) { name = "TerrainNormal-" + name };
                AssetDatabase.CreateAsset(texture, path);
            }
            float H(int x, int y) => relief[((y + N) % N) * N + (x + N) % N];
            var pixels = new Color[N * N];
            for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float dx = (H(x + 1, y) - H(x - 1, y)) * strength, dy = (H(x, y + 1) - H(x, y - 1)) * strength;
                var n = new Vector3(-dx, -dy, 1).normalized;
                pixels[y * N + x] = new Color(n.x * .5f + .5f, n.y * .5f + .5f, n.z * .5f + .5f, 1);
            }
            texture.SetPixels(pixels);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.anisoLevel = 4;
            texture.Apply(true);
            EditorUtility.SetDirty(texture);
            return texture;
        }
    }
}
